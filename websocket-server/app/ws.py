"""Game + lobby WebSocket loop for the new backend (S2.3b).

A faithful port of websocket-server/main.py's WS logic onto the S2.2 Postgres
repository + the machi_koro_engine package. Preserves the Stage-0 properties:
restart-survival (TASK-001), per-seat WS auth (TASK-002, 4401 on bad token),
write-then-broadcast (QA-001), and rematch-safe scores (TASK-004/QA-006).

PARALLEL BUILD — not serving live. The MVP still runs main.py on MySQL; the
container entrypoint switches to app.main:app at the S2.6/S2.7 cutover.
"""
import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from machi_koro_engine import (
    calculate_scores, config_for, config_for_version, create_initial_state, handle_action,
)
from persistence import repository as repo
from persistence.database import async_session

from app.auth import verify_ws_token

router = APIRouter()

# ── In-memory connection/room state (per backend process) ─────────────────────
lobby_rooms: dict[str, dict[str, WebSocket]] = {}   # code -> {seat_str -> ws}
game_rooms: dict[str, dict[str, WebSocket]] = {}    # code -> {seat_str -> ws}
game_states: dict[str, dict] = {}                   # code -> authoritative state dict
_state_locks: dict[str, asyncio.Lock] = {}          # code -> per-game serialization lock


def _lock_for(code: str) -> asyncio.Lock:
    # Safe without its own lock: only called from coroutines on the single event
    # loop, with no await between get and set.
    lock = _state_locks.get(code)
    if lock is None:
        lock = asyncio.Lock()
        _state_locks[code] = lock
    return lock


def _log_task_exception(task: asyncio.Task) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as e:  # surface detached-task errors instead of swallowing them
        print(f"[game] background task error: {e}")


async def broadcast(rooms: dict, code: str, message: dict) -> None:
    if code not in rooms:
        return
    if message.get("event") == "state_update":
        message = {**message, "connected_count": len(rooms[code])}
    dead = []
    for seat, ws in rooms[code].items():
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead.append(seat)
    for seat in dead:
        rooms[code].pop(seat, None)


# ── Persistence wrappers (repo, session-per-call — mirrors main.py's conn-per-op) ─

async def _persist_state(code: str) -> None:
    """Write-then-broadcast: persist the authoritative in-memory state per action.
    A failed write is logged but does not interrupt play."""
    state = game_states.get(code)
    if state is None:
        return
    try:
        async with async_session() as session:
            await repo.save_state(session, code, state)
    except Exception as e:
        print(f"[game] state save error for {code}: {e}")


async def _persist_scores(code: str) -> None:
    """On finish, upsert one row per registered player. Idempotent two ways: the
    in-memory scores_saved fast-path here + the repo's UNIQUE(table_id, game_seq,
    user_id) upsert (authoritative). game_seq distinguishes rematches (QA-006)."""
    state = game_states.get(code)
    if state is None:
        return
    if state.get("phase") != "finished" or state.get("scores_saved"):
        return
    try:
        async with async_session() as session:
            await repo.save_scores(session, code, state)
        state["scores_saved"] = True  # set only after a clean write
    except Exception as e:
        print(f"[game] save_scores error for {code}: {e}")


async def _table_config(code: str):
    """Composed config from the table's persisted (game_version, sharp,
    variable_supply) — the rematch path, so all three flags survive (state['version']
    alone doesn't encode the supply mode). None on miss so the caller can fall back."""
    try:
        async with async_session() as session:
            table = await repo.get_table(session, code)
        if not table:
            return None
        return config_for(table.game_version, table.sharp, table.variable_supply)
    except Exception as e:
        print(f"[game] table config read error for {code}: {e}")
        return None


async def _load_or_create_state(code: str):
    """Rehydrate from Postgres if a state row exists (restart-survival); else build
    the initial state from the table's players + flags and persist it. Only for a
    started (status='playing') table."""
    try:
        async with async_session() as session:
            table = await repo.get_table_with_players(session, code)
            if not table or table.status != "playing":
                return None
            existing = await repo.load_state(session, code)
            if existing is not None:
                return existing
            players = [
                {"seat": p.seat, "display_name": p.display_name, "user_id": p.user_id}
                for p in sorted(table.players, key=lambda p: p.seat)
            ]
            if not players:
                return None
            state = create_initial_state(
                players,
                config=config_for(table.game_version, table.sharp, table.variable_supply),
            )
            await repo.save_state(session, code, state)  # persist the initial state
        return state
    except Exception as e:
        print(f"[game] state load error for {code}: {e}")
        return None


# ── Lobby WebSocket (no token gate, as today) ─────────────────────────────────

@router.websocket("/ws/{code}/lobby/{seat}")
async def lobby_ws(websocket: WebSocket, code: str, seat: str):
    await websocket.accept()
    lobby_rooms.setdefault(code, {})[seat] = websocket
    await broadcast(lobby_rooms, code, {"event": "player_joined", "seat": seat})

    try:
        while True:
            msg = json.loads(await websocket.receive_text())
            if "seat" not in msg:  # don't clobber a carried seat (e.g. player_kicked)
                msg["seat"] = seat
            await broadcast(lobby_rooms, code, msg)
    except WebSocketDisconnect:
        lobby_rooms.get(code, {}).pop(seat, None)
        if seat == "0":  # host occupies seat 0 — host leaving closes the table
            await broadcast(lobby_rooms, code, {"event": "table_closed"})
            lobby_rooms.pop(code, None)
            await _delete_waiting_table(code)
        else:
            await broadcast(lobby_rooms, code, {"event": "player_left", "seat": seat})
            await _remove_waiting_player(code, int(seat))
            if not lobby_rooms.get(code):
                lobby_rooms.pop(code, None)
                await _delete_waiting_table(code)


async def _delete_waiting_table(code: str) -> None:
    try:
        async with async_session() as session:
            await repo.delete_waiting_table(session, code)
    except Exception as e:
        print(f"[lobby] failed to delete table {code}: {e}")


async def _remove_waiting_player(code: str, seat: int) -> None:
    try:
        async with async_session() as session:
            await repo.remove_waiting_player(session, code, seat)
    except Exception as e:
        print(f"[lobby] failed to remove player seat={seat} from table {code}: {e}")


# ── Game WebSocket ─────────────────────────────────────────────────────────────

@router.websocket("/ws/{code}/game/{seat}")
async def game_ws(websocket: WebSocket, code: str, seat: int):
    await websocket.accept()

    # Authenticate before touching game state — token binds (code, seat, identity).
    if not verify_ws_token(websocket.query_params.get("token", ""), code, seat):
        await websocket.close(code=4401)
        return

    is_reconnect = (
        code in game_states
        and str(seat) not in game_rooms.get(code, {})
        and any(p["seat"] == seat for p in game_states[code]["players"])
    )
    game_rooms.setdefault(code, {})[str(seat)] = websocket

    if is_reconnect:
        rejoiner = next((p for p in game_states[code]["players"] if p["seat"] == seat), None)
        if rejoiner:
            await broadcast(game_rooms, code, {
                "event": "player_rejoined_game", "name": rejoiner["name"], "seat": seat,
            })

    # Load/create under the lock + re-check so two simultaneous connects (a forced
    # restart reconnecting everyone at once) can't both build/insert.
    if code not in game_states:
        async with _lock_for(code):
            if code not in game_states:
                state = await _load_or_create_state(code)
                if state:
                    game_states[code] = state

    if code in game_states:
        await websocket.send_text(json.dumps({
            "event": "state_update",
            "state": game_states[code],
            "connected_count": len(game_rooms.get(code, {})),
        }))

    try:
        while True:
            msg = json.loads(await websocket.receive_text())
            if code not in game_states:
                continue

            # Reaction touches no state — handle outside the lock.
            if msg.get("event") == "reaction":
                await broadcast(game_rooms, code, {
                    "event": "reaction", "seat": seat, "emoji": msg.get("emoji", ""),
                })
                continue

            # Serialize state read/mutate/persist per code: the lock is taken AFTER
            # receive_text (never held across the blocking receive — no head-of-line
            # blocking), so save_state can't commit out of order vs auto-win/new_game.
            async with _lock_for(code):
                if code not in game_states:
                    continue
                state = game_states[code]

                # New game / rematch at the same table.
                if msg.get("event") == "new_game" and state.get("phase") == "finished":
                    connected = game_rooms.get(code, {})
                    if len(connected) >= 2:
                        connected_seats = sorted(int(s) for s in connected)
                        players_info = [
                            {"seat": s,
                             "display_name": next(p["name"] for p in state["players"] if p["seat"] == s),
                             "user_id": next((p.get("user_id") for p in state["players"] if p["seat"] == s), None)}
                            for s in connected_seats
                        ]
                        cfg = await _table_config(code) or config_for_version(state.get("version"))
                        new_state = create_initial_state(players_info, config=cfg)
                        new_state["active_seat"] = connected_seats[0]
                        new_state["game_seq"] = state.get("game_seq", 0) + 1  # QA-006
                        game_states[code] = new_state
                        await _persist_state(code)
                        await broadcast(game_rooms, code, {"event": "state_update", "state": new_state})
                    continue

                result = handle_action(state, seat, msg)

                if result.get("broadcast"):
                    # On a finish, persist scores first so the scores_saved flag is in
                    # the snapshot save_state writes. Persist before broadcasting so
                    # players never see a state that isn't durably saved (QA-001).
                    if state.get("phase") == "finished":
                        await _persist_scores(code)
                    await _persist_state(code)
                    await broadcast(game_rooms, code, {"event": "state_update", "state": state})

                if result.get("announce"):
                    await broadcast(game_rooms, code, {"event": "game_toast", "text": result["announce"]})

                if result.get("coin_changes"):
                    for seat_str, ws in list(game_rooms.get(code, {}).items()):
                        changes = result["coin_changes"].get(int(seat_str), [])
                        if changes:
                            try:
                                await ws.send_text(json.dumps({"event": "coin_event", "changes": changes}))
                            except Exception:
                                pass

                if result.get("transfers"):
                    for transfer_text in result["transfers"]:
                        await broadcast(game_rooms, code, {"event": "game_toast", "text": transfer_text})

                if result.get("prompt"):
                    active_ws = game_rooms[code].get(str(state["active_seat"]))
                    if active_ws:
                        try:
                            await active_ws.send_text(json.dumps({
                                "event": "prompt",
                                "text": result["prompt"]["text"],
                                "promptId": result["prompt"]["id"],
                            }))
                        except Exception:
                            pass

    except WebSocketDisconnect:
        game_rooms.get(code, {}).pop(str(seat), None)
        if code in game_states:
            state = game_states[code]
            leaving = next((p for p in state["players"] if p["seat"] == seat), None)
            name = leaving["name"] if leaving else f"Player {seat}"
            await broadcast(game_rooms, code, {"event": "player_left_game", "name": name, "seat": seat})
            delay = 3 if len(game_rooms.get(code, {})) <= 1 else 15
            task = asyncio.create_task(_delayed_auto_win(code, seat, delay))
            task.add_done_callback(_log_task_exception)

        if not game_rooms.get(code):
            game_states.pop(code, None)
            game_rooms.pop(code, None)
            _state_locks.pop(code, None)


async def _delayed_auto_win(code: str, seat: int, delay: int = 15) -> None:
    """After a grace window, award the win if exactly one player remains. Serialized
    against the main loop so this terminal write can't interleave with an action."""
    await asyncio.sleep(delay)
    async with _lock_for(code):
        if code not in game_states:
            return
        state = game_states[code]
        if state.get("phase") == "finished":
            return
        if str(seat) in game_rooms.get(code, {}):
            return  # player reconnected
        remaining = game_rooms.get(code, {})
        if len(remaining) == 1:
            winner_seat = int(next(iter(remaining)))
            winner = next((p for p in state["players"] if p["seat"] == winner_seat), None)
            if winner:
                state["winner"] = winner_seat
                state["phase"] = "finished"
                state["scores"] = calculate_scores(state)
                state["log"].append(f"🏆 {winner['name']} wins — all other players left!")
                await _persist_scores(code)
                await _persist_state(code)
                await broadcast(game_rooms, code, {"event": "state_update", "state": state})
