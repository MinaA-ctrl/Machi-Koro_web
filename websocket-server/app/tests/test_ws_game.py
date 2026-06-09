"""S2.3b — game/lobby WebSocket play over Postgres, via TestClient WS.

Covers the ACs + Stage-0 properties: a finished game writes rematch-safe scores,
restart-survival (reload mid-game from Postgres), per-seat auth rejection, and
interactive flows (a Harbor prompt + a Sharp cleaning pick on a Harbour+Sharp+VS
game). Determinism via monkeypatching the engine's roll_die.
"""
import asyncio
import uuid

import pytest
from fastapi import WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app import ws as ws_mod
from app.auth import mint_ws_token
from persistence.database import DATABASE_URL
from persistence.models import Player, Score, Table


# ── helpers ──────────────────────────────────────────────────────────────────

def _code() -> str:
    return "MK-" + uuid.uuid4().hex[:6].upper()


def _run(coro):
    """Run an async DB helper on a throwaway loop (separate from the TestClient
    portal loop), with a NullPool engine that's disposed each call."""
    async def _wrap():
        eng = create_async_engine(DATABASE_URL, poolclass=NullPool)
        sm = async_sessionmaker(eng, expire_on_commit=False)
        try:
            async with sm() as s:
                return await coro(s)
        finally:
            await eng.dispose()
    return asyncio.run(_wrap())


def seed_started(code, *, game_version="harbour", sharp=False, variable_supply=False, players):
    """Insert a started (status='playing') table + players directly, so the game WS
    builds initial state from them on first connect. `players` = [(seat, name, user_id)]."""
    async def _seed(s):
        t = Table(
            join_code=code, name="T", creator_id="user:1", status="playing",
            game_version=game_version, sharp=sharp, variable_supply=variable_supply,
        )
        s.add(t)
        await s.flush()
        for seat, name, uid in players:
            s.add(Player(table_id=t.id, seat=seat, display_name=name, user_id=uid,
                         identity=f"user:{uid}" if uid else f"guest:{seat}", is_host=(seat == 0)))
        await s.commit()
    _run(_seed)


def score_rows(code):
    async def _q(s):
        rows = (await s.execute(
            select(Score.user_id, Score.game_seq, Score.won)
            .join(Table, Table.id == Score.table_id)
            .where(Table.join_code == code)
        )).all()
        return [tuple(r) for r in rows]
    return _run(_q)


def connect(client, code, seat, *, identity="user:10", token=None):
    tok = token if token is not None else mint_ws_token(code, seat, identity)
    return client.websocket_connect(f"/ws/{code}/game/{seat}?token={tok}")


def recv_event(ws, event, max_msgs=12):
    """Receive (draining intervening toasts/coin_events) until `event` appears."""
    for _ in range(max_msgs):
        msg = ws.receive_json()
        if msg.get("event") == event:
            return msg
    raise AssertionError(f"did not receive {event!r} within {max_msgs} messages")


# ── auth (TASK-002) ────────────────────────────────────────────────────────────

def test_auth_rejects_bad_missing_and_wrong_seat_tokens(client):
    code = _code()
    seed_started(code, players=[(0, "A", 10), (1, "B", 20)])

    for url in (
        f"/ws/{code}/game/0?token=garbage",                       # bad
        f"/ws/{code}/game/0",                                      # missing
        f"/ws/{code}/game/1?token={mint_ws_token(code, 0, 'user:10')}",  # seat-0 token on seat 1
    ):
        with client.websocket_connect(url) as wsx:
            with pytest.raises(WebSocketDisconnect) as ei:
                wsx.receive_json()
        assert ei.value.code == 4401


# ── write-then-broadcast (QA-001) + restart-survival (TASK-001) ───────────────

def test_action_persists_then_restart_reloads_from_postgres(client, monkeypatch):
    code = _code()
    seed_started(code, players=[(0, "A", 10), (1, "B", 20)])
    monkeypatch.setattr("machi_koro_engine.game_engine.roll_die", lambda: 1)  # wheat_field hits

    with connect(client, code, 0, identity="user:10") as ws0:
        recv_event(ws0, "state_update")                 # initial state
        ws0.send_json({"event": "roll", "dice_count": 1})
        after_roll = recv_event(ws0, "state_update")["state"]
        assert after_roll["last_roll"] == 1

    # Simulate a backend restart: drop the in-memory state; it must reload from DB.
    ws_mod.game_states.pop(code, None)
    with connect(client, code, 0, identity="user:10") as ws0:
        reloaded = recv_event(ws0, "state_update")["state"]
    assert reloaded == after_roll                        # rehydrated identically


# ── finish writes scores; rematch-safe (TASK-004 / QA-006) ────────────────────

def _force_win(code, seat):
    """Shortcut the active player to one landmark short with cash, so a single
    build-landmark action finishes the game (avoids grinding ~50 coins)."""
    state = ws_mod.game_states[code]
    state["active_seat"] = seat
    state["phase"] = "build"
    p = next(p for p in state["players"] if p["seat"] == seat)
    for lm in p["landmarks"]:
        lm["built"] = True
    target = next(lm for lm in p["landmarks"] if lm["id"] != "city_hall")
    target["built"] = False
    p["coins"] = 100
    return target["id"]


def test_finish_writes_scores_and_rematch_is_safe(client):
    code = _code()
    seed_started(code, players=[(0, "A", 10), (1, "B", 20)])

    with connect(client, code, 0, identity="user:10") as ws0, \
         connect(client, code, 1, identity="user:20") as ws1:
        recv_event(ws0, "state_update")
        recv_event(ws1, "state_update")

        # Game 1 — seat 0 (user 10) wins.
        lm = _force_win(code, 0)
        ws0.send_json({"event": "build", "type": "landmark", "id": lm})
        won = recv_event(ws0, "state_update")["state"]
        assert won["phase"] == "finished" and won["winner"] == 0

        rows = score_rows(code)
        assert sorted(rows) == [(10, 0, True), (20, 0, False)]   # one row per registered player

        # Rematch — new_game needs ≥2 connected; bumps game_seq → fresh score rows.
        ws0.send_json({"event": "new_game"})
        new = recv_event(ws0, "state_update")["state"]
        assert new["game_seq"] == 1 and new["phase"] == "roll"
        recv_event(ws1, "state_update")  # seat 1 also gets the rematch broadcast

        lm2 = _force_win(code, new["active_seat"])
        ws0.send_json({"event": "build", "type": "landmark", "id": lm2})
        recv_event(ws0, "state_update")

    # Two games at one table → distinct game_seq rows both persist (rematch-safe).
    rows = score_rows(code)
    assert {(u, g) for u, g, _ in rows} == {(10, 0), (20, 0), (10, 1), (20, 1)}


# ── interactive flow: Harbor prompt ────────────────────────────────────────────

def test_harbor_prompt_interactive_over_ws(client, monkeypatch):
    code = _code()
    seed_started(code, players=[(0, "A", 10), (1, "B", 20)])  # Harbour has the Harbor landmark
    rolls = iter([5, 5])
    monkeypatch.setattr("machi_koro_engine.game_engine.roll_die", lambda: next(rolls))

    with connect(client, code, 0, identity="user:10") as ws0:
        recv_event(ws0, "state_update")
        active = next(p for p in ws_mod.game_states[code]["players"] if p["seat"] == 0)
        for lm in active["landmarks"]:
            if lm["id"] in ("harbor", "train_station"):
                lm["built"] = True  # train_station → 2 dice; harbor → +2 prompt at 10+

        ws0.send_json({"event": "roll", "dice_count": 2})        # 5+5 = 10
        prompt = recv_event(ws0, "prompt")
        assert prompt["promptId"] == "harbor_bonus"

        ws0.send_json({"event": "prompt_response", "answer": True})
        resolved = recv_event(ws0, "state_update")["state"]
        assert resolved["phase"] in ("build", "tv_station", "tuna_roll")  # roll resolved


# ── Sharp + Variable Supply + interactive Sharp pick ──────────────────────────

def test_sharp_vs_game_with_cleaning_company_pick(client, monkeypatch):
    code = _code()
    seed_started(code, sharp=True, variable_supply=True, players=[(0, "A", 10), (1, "B", 20)])
    rolls = iter([3, 5])  # → 8 = Cleaning Company
    monkeypatch.setattr("machi_koro_engine.game_engine.roll_die", lambda: next(rolls))

    with connect(client, code, 0, identity="user:10") as ws0:
        initial = recv_event(ws0, "state_update")["state"]
        assert initial["version"] == "Harbour + Sharp"
        assert "deck" in initial and len(initial["supply"]) == 10   # Variable Supply active

        st = ws_mod.game_states[code]
        active = next(p for p in st["players"] if p["seat"] == 0)
        active["cards"]["cleaning_company"] = 1
        next(lm for lm in active["landmarks"] if lm["id"] == "train_station")["built"] = True
        next(p for p in st["players"] if p["seat"] == 1)["cards"]["cafe"] = 1  # a target type

        ws0.send_json({"event": "roll", "dice_count": 2})           # 3+5 = 8
        rolled = recv_event(ws0, "state_update")["state"]
        assert rolled["phase"] == "cleaning_company"
        assert "cafe" in rolled["pending_prompt"]["targets"]

        ws0.send_json({"event": "cleaning_company_pick", "card_type": "cafe"})
        after = recv_event(ws0, "state_update")["state"]
        assert after["phase"] == "build"
        opp = next(p for p in after["players"] if p["seat"] == 1)
        assert opp["renovation"].get("cafe") == 1                   # closed for renovation
        assert next(p for p in after["players"] if p["seat"] == 0)["coins"] >= 1  # +1 per closed
