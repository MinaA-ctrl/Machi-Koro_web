import asyncio
import base64
import hashlib
import hmac
import json
import os
import time
import aiomysql
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from game_engine import create_initial_state, handle_action, calculate_scores
from game_config import config_for_version, config_for

# Shared HMAC secret for verifying game WS tokens (must match the WordPress service)
MK_WS_SECRET = os.getenv('MK_WS_SECRET', '')


def verify_ws_token(token: str, code: str, seat: int) -> bool:
    """Verify a per-seat game token issued by WordPress (see api.php mk_ws_token).

    Recomputes HMAC-SHA256 over code|seat|identity|exp. Because `seat` is part of
    the signed payload, a token minted for one seat cannot be replayed on another.
    Returns False on any malformed/expired/mismatched token.
    """
    if not MK_WS_SECRET:
        print("[auth] MK_WS_SECRET is not set — rejecting all game connections")
        return False
    if not token:
        return False
    try:
        pad = '=' * (-len(token) % 4)
        plain = base64.urlsafe_b64decode(token + pad).decode()
        identity, exp_str, sig = plain.rsplit('|', 2)
        exp = int(exp_str)
    except Exception:
        return False
    if exp < time.time():
        return False
    msg = f"{code}|{seat}|{identity}|{exp}"
    expected = hmac.new(MK_WS_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)

app = FastAPI()

# code -> {seat_str -> WebSocket}
lobby_rooms: dict[str, dict[str, WebSocket]] = {}
game_rooms:  dict[str, dict[str, WebSocket]] = {}

# code -> game state dict (in-memory)
game_states: dict[str, dict] = {}

# code -> table_id (cached so we don't re-query the table on every action)
table_ids: dict[str, int] = {}

# code -> asyncio.Lock serializing state load/mutation/persist for that game,
# so a forced-restart double-connect or a grace-window auto-win can't race.
_state_locks: dict[str, asyncio.Lock] = {}


def _lock_for(code: str) -> asyncio.Lock:
    # Safe without its own lock: only ever called from coroutines on the single
    # event loop, and there is no await between the get and the set.
    lock = _state_locks.get(code)
    if lock is None:
        lock = asyncio.Lock()
        _state_locks[code] = lock
    return lock


def _log_task_exception(task: asyncio.Task):
    """Done-callback so detached tasks surface errors instead of swallowing them."""
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[game] background task error: {e}")

DB = dict(
    host     = os.getenv('DB_HOST', 'db'),
    db       = os.getenv('DB_NAME', 'machikoro'),
    user     = os.getenv('DB_USER', 'machiuser'),
    password = os.getenv('DB_PASSWORD', 'machipass'),
)


async def db_connect():
    return await aiomysql.connect(**DB)


async def broadcast(rooms: dict, code: str, message: dict):
    if code not in rooms:
        return
    # Attach live connected count whenever we broadcast a state update
    if message.get('event') == 'state_update':
        message = {**message, 'connected_count': len(rooms[code])}
    dead = []
    for seat, ws in rooms[code].items():
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead.append(seat)
    for seat in dead:
        rooms[code].pop(seat, None)


# ── Lobby WebSocket ────────────────────────────────────────────────────────────

@app.websocket("/ws/{code}/lobby/{seat}")
async def lobby_ws(websocket: WebSocket, code: str, seat: str):
    await websocket.accept()

    lobby_rooms.setdefault(code, {})[seat] = websocket
    await broadcast(lobby_rooms, code, {'event': 'player_joined', 'seat': seat})

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            # Don't overwrite 'seat' if the message already carries one
            # (e.g. player_kicked contains the target's seat, not the sender's)
            if 'seat' not in msg:
                msg['seat'] = seat
            await broadcast(lobby_rooms, code, msg)
    except WebSocketDisconnect:
        lobby_rooms.get(code, {}).pop(seat, None)

        if seat == '0':  # host always occupies seat 0
            await broadcast(lobby_rooms, code, {'event': 'table_closed'})
            lobby_rooms.pop(code, None)
            await _delete_waiting_table(code)
        else:
            await broadcast(lobby_rooms, code, {'event': 'player_left', 'seat': seat})
            await _remove_waiting_player(code, int(seat))

            if not lobby_rooms.get(code):
                lobby_rooms.pop(code, None)
                await _delete_waiting_table(code)


async def _delete_waiting_table(code: str):
    try:
        conn = await db_connect()
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id FROM wp_mk_tables WHERE code=%s AND status='waiting'", (code,)
            )
            row = await cur.fetchone()
            if row:
                table_id = row[0]
                await cur.execute("DELETE FROM wp_mk_players WHERE table_id=%s", (table_id,))
                await cur.execute("DELETE FROM wp_mk_tables WHERE id=%s", (table_id,))
                await conn.commit()
        conn.close()
    except Exception as e:
        print(f"[lobby] failed to delete table {code}: {e}")


async def _remove_waiting_player(code: str, seat: int):
    try:
        conn = await db_connect()
        async with conn.cursor() as cur:
            await cur.execute(
                """DELETE p FROM wp_mk_players p
                   INNER JOIN wp_mk_tables t ON t.id = p.table_id
                   WHERE t.code = %s AND t.status = 'waiting' AND p.seat = %s""",
                (code, seat)
            )
            await conn.commit()
        conn.close()
    except Exception as e:
        print(f"[lobby] failed to remove player seat={seat} from table {code}: {e}")


# ── Game WebSocket ─────────────────────────────────────────────────────────────

@app.websocket("/ws/{code}/game/{seat}")
async def game_ws(websocket: WebSocket, code: str, seat: int):
    await websocket.accept()

    # Authenticate before doing anything with game state. The token binds this
    # connection to (code, seat, identity); reject mismatches with code 4401.
    token = websocket.query_params.get('token', '')
    if not verify_ws_token(token, code, seat):
        await websocket.close(code=4401)
        return

    # Detect reconnection: seat was in the game but lost its WS connection
    is_reconnect = (
        code in game_states
        and str(seat) not in game_rooms.get(code, {})
        and any(p['seat'] == seat for p in game_states[code]['players'])
    )

    game_rooms.setdefault(code, {})[str(seat)] = websocket

    if is_reconnect:
        state = game_states[code]
        rejoiner = next((p for p in state['players'] if p['seat'] == seat), None)
        if rejoiner:
            await broadcast(game_rooms, code, {
                'event': 'player_rejoined_game',
                'name':  rejoiner['name'],
                'seat':  seat,
            })

    # Load or create state on first connection to this game room.
    # Lock + re-check so two simultaneous connects (a forced restart reconnecting
    # every client at once) can't both run the check-then-insert and duplicate rows.
    if code not in game_states:
        async with _lock_for(code):
            if code not in game_states:
                state = await _load_or_create_state(code)
                if state:
                    game_states[code] = state

    # Send current state immediately to the connecting player
    if code in game_states:
        await websocket.send_text(json.dumps({
            'event':           'state_update',
            'state':           game_states[code],
            'connected_count': len(game_rooms.get(code, {})),
        }))

    try:
        while True:
            raw  = await websocket.receive_text()
            msg  = json.loads(raw)

            if code not in game_states:
                continue

            # ── Reaction (touches no state — handled outside the lock) ──────────
            if msg.get('event') == 'reaction':
                await broadcast(game_rooms, code, {
                    'event': 'reaction',
                    'seat':  seat,
                    'emoji': msg.get('emoji', ''),
                })
                continue

            # Everything below reads, mutates, and/or persists state. Serialize it
            # per code so an action's save_state can't commit out of order against
            # _delayed_auto_win or new_game (the finished snapshot must be the last
            # write). The lock is acquired AFTER receive_text, so it is never held
            # across the blocking receive — no head-of-line blocking between players.
            async with _lock_for(code):
                if code not in game_states:
                    continue
                state = game_states[code]

                # ── New game at same table ──────────────────────────────────────
                if msg.get('event') == 'new_game' and state.get('phase') == 'finished':
                    connected = game_rooms.get(code, {})
                    if len(connected) >= 2:
                        connected_seats = sorted(int(s) for s in connected)
                        players_info = [
                            {'seat': s,
                             'display_name': next(
                                 p['name'] for p in state['players'] if p['seat'] == s
                             ),
                             'user_id': next(
                                 (p.get('user_id') for p in state['players'] if p['seat'] == s),
                                 None
                             )}
                            for s in connected_seats
                        ]
                        # A rematch keeps the table's version: derive the config
                        # from the finished game's stored label.
                        new_state = create_initial_state(
                            players_info, config=config_for_version(state.get('version'))
                        )
                        # Start with the lowest-numbered connected seat
                        new_state['active_seat'] = connected_seats[0]
                        # Bump the per-game discriminator so this rematch's scores
                        # write under a fresh (table_id, game_seq) — game 1's rows
                        # no longer mask game 2's (QA-006).
                        new_state['game_seq'] = state.get('game_seq', 0) + 1
                        game_states[code] = new_state
                        await save_state(code)
                        await broadcast(game_rooms, code, {
                            'event': 'state_update',
                            'state': new_state,
                        })
                    continue

                result = handle_action(state, seat, msg)

                if result.get('broadcast'):
                    # On a finish, persist the scoreboard first so the scores_saved
                    # flag is included in the snapshot save_state writes below.
                    if state.get('phase') == 'finished':
                        await save_scores(code)
                    # Persist before broadcasting so players never observe a state
                    # that isn't already durably saved (survives a crash in between).
                    await save_state(code)
                    await broadcast(game_rooms, code, {
                        'event': 'state_update',
                        'state': state,
                    })

                if result.get('announce'):
                    await broadcast(game_rooms, code, {
                        'event': 'game_toast',
                        'text':  result['announce'],
                    })

                if result.get('coin_changes'):
                    for seat_str, ws in list(game_rooms.get(code, {}).items()):
                        seat_changes = result['coin_changes'].get(int(seat_str), [])
                        if seat_changes:
                            try:
                                await ws.send_text(json.dumps({
                                    'event':   'coin_event',
                                    'changes': seat_changes,
                                }))
                            except Exception:
                                pass

                if result.get('transfers'):
                    for transfer_text in result['transfers']:
                        await broadcast(game_rooms, code, {
                            'event': 'game_toast',
                            'text':  transfer_text,
                        })

                if result.get('prompt'):
                    # Only the active player sees the prompt
                    active_ws = game_rooms[code].get(str(state['active_seat']))
                    if active_ws:
                        try:
                            await active_ws.send_text(json.dumps({
                                'event':    'prompt',
                                'text':     result['prompt']['text'],
                                'promptId': result['prompt']['id'],
                            }))
                        except Exception:
                            pass

    except WebSocketDisconnect:
        game_rooms.get(code, {}).pop(str(seat), None)

        # Announce the departure to remaining players
        if code in game_states:
            state = game_states[code]
            leaving = next((p for p in state['players'] if p['seat'] == seat), None)
            name = leaving['name'] if leaving else f"Player {seat}"
            await broadcast(game_rooms, code, {
                'event': 'player_left_game',
                'name':  name,
                'seat':  seat,
            })
            # Grace period before auto-win: short if only 1 player remains, longer otherwise
            remaining_after = len(game_rooms.get(code, {}))
            delay = 3 if remaining_after <= 1 else 15
            task = asyncio.create_task(_delayed_auto_win(code, seat, delay))
            task.add_done_callback(_log_task_exception)

        if not game_rooms.get(code):
            game_states.pop(code, None)
            game_rooms.pop(code, None)
            table_ids.pop(code, None)
            _state_locks.pop(code, None)


async def _delayed_auto_win(code: str, seat: int, delay: int = 15):
    """Wait then auto-win if only one player remains. Short delay when 1 player already left."""
    await asyncio.sleep(delay)
    # Serialize against the main loop's load/persist so this terminal write can't
    # interleave with — or be overwritten by — a concurrent action's save_state.
    async with _lock_for(code):
        if code not in game_states:
            return
        state = game_states[code]
        # Re-check inside the lock: a player may have acted (finishing the game) or
        # reconnected during the grace window.
        if state.get('phase') == 'finished':
            return
        if str(seat) in game_rooms.get(code, {}):
            return  # Player reconnected
        remaining = game_rooms.get(code, {})
        if len(remaining) == 1:
            winner_seat = int(next(iter(remaining)))
            winner = next((p for p in state['players'] if p['seat'] == winner_seat), None)
            if winner:
                state['winner'] = winner_seat
                state['phase']  = 'finished'
                state['scores'] = calculate_scores(state)
                state['log'].append(f"🏆 {winner['name']} wins — all other players left!")
                await save_scores(code)
                await save_state(code)
                await broadcast(game_rooms, code, {
                    'event': 'state_update',
                    'state': state,
                })


async def save_state(code: str):
    """Persist the authoritative in-memory state for `code` to wp_mk_game_states.

    Awaited after every broadcasting action so a forced WS restart restores the
    full game. The in-memory state stays authoritative; a failed write is logged
    but does not interrupt play.
    """
    state = game_states.get(code)
    if state is None:
        return
    table_id = table_ids.get(code)
    if table_id is None:
        print(f"[game] save_state skipped — no table_id cached for {code}")
        return
    try:
        conn = await db_connect()
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE wp_mk_game_states SET state=%s WHERE table_id=%s",
                (json.dumps(state), table_id),
            )
            await conn.commit()
        conn.close()
    except Exception as e:
        print(f"[game] state save error for {code}: {e}")


async def save_scores(code: str):
    """Write one wp_mk_scores row per registered player when a game finishes.

    Guests (user_id is None) are skipped. Idempotent two ways so neither finish
    path (check_win or _delayed_auto_win), a reconnect-triggered re-finish, nor a
    second WS replica can double-write:
      * fast path: in-memory state['scores_saved'] flag (persisted with the state);
      * authoritative: UNIQUE(table_id, game_seq, user_id) + ON DUPLICATE KEY
        UPDATE, so even a flag loss on restart or a concurrent replica converges
        to exactly one row per (game, player).
    game_seq distinguishes rematches at the same table_id (QA-006): without it,
    game 2's scores were masked by game 1's existing rows. Callers persist the
    flag via save_state after this returns.
    """
    state = game_states.get(code)
    if state is None:
        return
    if state.get('phase') != 'finished' or state.get('scores_saved'):
        return
    table_id = table_ids.get(code)
    if table_id is None:
        print(f"[game] save_scores skipped — no table_id cached for {code}")
        return

    winner = state.get('winner')
    game_seq = state.get('game_seq', 0)
    rows = [
        (p['user_id'], table_id, game_seq,
         sum(1 for lm in p['landmarks'] if lm['built'] and lm['id'] != 'city_hall'),
         p['coins'],
         1 if p['seat'] == winner else 0)
        for p in state['players']
        if p.get('user_id')  # registered players only; skip guests
    ]
    try:
        conn = await db_connect()
        async with conn.cursor() as cur:
            if rows:
                # UNIQUE(table_id, game_seq, user_id) makes this atomic and
                # idempotent — re-finishes, restart flag-loss, and concurrent
                # replicas all converge to one row per (game, player).
                await cur.executemany(
                    """INSERT INTO wp_mk_scores
                           (user_id, table_id, game_seq, landmarks_built, coins_at_end, won)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                           landmarks_built = VALUES(landmarks_built),
                           coins_at_end    = VALUES(coins_at_end),
                           won             = VALUES(won)""",
                    rows,
                )
                await conn.commit()
        conn.close()
        state['scores_saved'] = True  # set only after a clean write
    except Exception as e:
        print(f"[game] save_scores error for {code}: {e}")


async def _load_or_create_state(code: str):
    try:
        conn = await db_connect()
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, game_version, sharp FROM wp_mk_tables WHERE code=%s AND status='playing'",
                (code,)
            )
            table = await cur.fetchone()
            if not table:
                return None

            table_id = table['id']
            table_ids[code] = table_id  # cache for save_state / auto-win

            # Return existing state if already persisted
            await cur.execute(
                "SELECT state FROM wp_mk_game_states WHERE table_id=%s", (table_id,)
            )
            row = await cur.fetchone()
            if row:
                return json.loads(row['state'])

            # Build initial state from player list
            await cur.execute(
                """SELECT p.seat, p.user_id,
                          COALESCE(u.display_name, p.guest_name, 'Guest') AS display_name
                   FROM wp_mk_players p
                   LEFT JOIN wp_users u ON u.ID = p.user_id
                   WHERE p.table_id=%s ORDER BY p.seat""",
                (table_id,)
            )
            players = await cur.fetchall()
            if not players:
                return None

            # Build the right composed config from the table's (game_version, sharp)
            # (D-BE). config_for normalizes the base and layers Sharp when the flag
            # is set; unknown/missing base → Harbour, falsy sharp → no add-on.
            state = create_initial_state(
                players, config=config_for(table.get('game_version'), table.get('sharp'))
            )

            # ON DUPLICATE KEY UPDATE: if another process/connection inserted the
            # initial row in the race window, keep the existing row (don't clobber).
            await cur.execute(
                """INSERT INTO wp_mk_game_states (table_id, state) VALUES (%s, %s)
                   ON DUPLICATE KEY UPDATE table_id = table_id""",
                (table_id, json.dumps(state))
            )
            await conn.commit()
        conn.close()
        return state
    except Exception as e:
        print(f"[game] state load error for {code}: {e}")
        return None
