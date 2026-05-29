import asyncio
import json
import os
import aiomysql
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from game_engine import create_initial_state, handle_action, calculate_scores

app = FastAPI()

# code -> {seat_str -> WebSocket}
lobby_rooms: dict[str, dict[str, WebSocket]] = {}
game_rooms:  dict[str, dict[str, WebSocket]] = {}

# code -> game state dict (in-memory)
game_states: dict[str, dict] = {}

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

    # Load or create state on first connection to this game room
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

            state = game_states[code]

            # ── Reaction ──────────────────────────────────────────────────────
            if msg.get('event') == 'reaction':
                await broadcast(game_rooms, code, {
                    'event': 'reaction',
                    'seat':  seat,
                    'emoji': msg.get('emoji', ''),
                })
                continue

            # ── New game at same table ────────────────────────────────────────
            if msg.get('event') == 'new_game' and state.get('phase') == 'finished':
                connected = game_rooms.get(code, {})
                if len(connected) >= 2:
                    connected_seats = sorted(int(s) for s in connected)
                    players_info = [
                        {'seat': s, 'display_name': next(
                            p['name'] for p in state['players'] if p['seat'] == s
                        )}
                        for s in connected_seats
                    ]
                    new_state = create_initial_state(players_info)
                    # Start with the lowest-numbered connected seat
                    new_state['active_seat'] = connected_seats[0]
                    game_states[code] = new_state
                    await broadcast(game_rooms, code, {
                        'event': 'state_update',
                        'state': new_state,
                    })
                continue

            result = handle_action(state, seat, msg)

            if result.get('broadcast'):
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
            asyncio.create_task(_delayed_auto_win(code, seat, delay))

        if not game_rooms.get(code):
            game_states.pop(code, None)
            game_rooms.pop(code, None)


async def _delayed_auto_win(code: str, seat: int, delay: int = 15):
    """Wait then auto-win if only one player remains. Short delay when 1 player already left."""
    await asyncio.sleep(delay)
    if code not in game_states:
        return
    state = game_states[code]
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
            await broadcast(game_rooms, code, {
                'event': 'state_update',
                'state': state,
            })


async def _load_or_create_state(code: str):
    try:
        conn = await db_connect()
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id FROM wp_mk_tables WHERE code=%s AND status='playing'", (code,)
            )
            table = await cur.fetchone()
            if not table:
                return None

            table_id = table['id']

            # Return existing state if already persisted
            await cur.execute(
                "SELECT state FROM wp_mk_game_states WHERE table_id=%s", (table_id,)
            )
            row = await cur.fetchone()
            if row:
                return json.loads(row['state'])

            # Build initial state from player list
            await cur.execute(
                """SELECT p.seat,
                          COALESCE(u.display_name, p.guest_name, 'Guest') AS display_name
                   FROM wp_mk_players p
                   LEFT JOIN wp_users u ON u.ID = p.user_id
                   WHERE p.table_id=%s ORDER BY p.seat""",
                (table_id,)
            )
            players = await cur.fetchall()
            if not players:
                return None

            state = create_initial_state(players)

            await cur.execute(
                "INSERT INTO wp_mk_game_states (table_id, state) VALUES (%s, %s)",
                (table_id, json.dumps(state))
            )
            await conn.commit()
        conn.close()
        return state
    except Exception as e:
        print(f"[game] state load error for {code}: {e}")
        return None
