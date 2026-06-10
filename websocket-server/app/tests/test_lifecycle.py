"""Table-lifecycle cleanup — browse filter + reaper (deterministic via injected
old timestamps). Exercises the repo reaping functions directly (reap_once is the
thin scheduler wrapper that computes cutoffs from config and calls these).
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from persistence import repository as repo
from persistence.database import DATABASE_URL
from persistence.models import GameState, Table


def _now():
    return datetime.now(timezone.utc)


def _run(fn):
    async def _wrap():
        eng = create_async_engine(DATABASE_URL, poolclass=NullPool)
        sm = async_sessionmaker(eng, expire_on_commit=False)
        try:
            async with sm() as s:
                return await fn(s)
        finally:
            await eng.dispose()
    return asyncio.run(_wrap())


def _code():
    return "MK-" + uuid.uuid4().hex[:6].upper()


async def _add_table(s, *, status, age_min, is_public=True, name="T", code=None):
    t = Table(join_code=code or _code(), name=name, creator_id="guest:1", status=status,
              is_public=is_public, created_at=_now() - timedelta(minutes=age_min))
    s.add(t)
    await s.flush()
    return t


async def _add_state(s, table_id, idle_min):
    s.add(GameState(table_id=table_id, state={}, game_seq=0,
                    updated_at=_now() - timedelta(minutes=idle_min)))


async def _status_by_code(s, code):
    return await s.scalar(select(Table.status).where(Table.join_code == code))


# ── browse filter ──────────────────────────────────────────────────────────────

def test_browse_hides_stale_waiting_shows_fresh(client):
    fresh, stale = _code(), _code()

    async def seed(s):
        await _add_table(s, status="waiting", age_min=1, name="Fresh", code=fresh)
        await _add_table(s, status="waiting", age_min=90, name="Stale", code=stale)  # > 30 min
        await s.commit()
    _run(seed)

    codes = {r["code"] for r in client.get("/tables").json()}
    assert fresh in codes and stale not in codes


# ── reaper: stale waiting ──────────────────────────────────────────────────────

def test_reaper_deletes_stale_waiting_keeps_fresh():
    fresh, stale = _code(), _code()

    async def go(s):
        await _add_table(s, status="waiting", age_min=1, code=fresh)
        await _add_table(s, status="waiting", age_min=90, code=stale)
        await s.commit()
        deleted = await repo.delete_stale_waiting(s, _now() - timedelta(minutes=30))
        return deleted, await _status_by_code(s, fresh), await _status_by_code(s, stale)

    deleted, fresh_status, stale_status = _run(go)
    assert deleted == 1
    assert fresh_status == "waiting"   # recent waiting untouched
    assert stale_status is None        # stale deleted (cascade)


# ── reaper: abandoned playing ──────────────────────────────────────────────────

def test_reaper_abandons_idle_playing_keeps_recent():
    idle, recent, nostate_old, nostate_new = _code(), _code(), _code(), _code()

    async def go(s):
        t_idle = await _add_table(s, status="playing", age_min=200, code=idle)
        await _add_state(s, t_idle.id, idle_min=200)               # last save 200 min ago
        t_recent = await _add_table(s, status="playing", age_min=200, code=recent)
        await _add_state(s, t_recent.id, idle_min=1)               # last save just now
        await _add_table(s, status="playing", age_min=200, code=nostate_old)   # no state, old
        await _add_table(s, status="playing", age_min=5, code=nostate_new)     # no state, recent
        await s.commit()

        marked = await repo.abandon_idle_playing(s, _now() - timedelta(minutes=120))
        return (marked, await _status_by_code(s, idle), await _status_by_code(s, recent),
                await _status_by_code(s, nostate_old), await _status_by_code(s, nostate_new))

    marked, idle_st, recent_st, nostate_old_st, nostate_new_st = _run(go)
    assert marked == 2
    assert idle_st == "abandoned"        # stale game_states save → abandoned
    assert recent_st == "playing"        # recent activity → untouched
    assert nostate_old_st == "abandoned" # no state + old created_at → abandoned
    assert nostate_new_st == "playing"   # no state but recent → untouched


def test_reaper_leaves_waiting_and_finished_alone():
    waiting, finished = _code(), _code()

    async def go(s):
        await _add_table(s, status="waiting", age_min=300, code=waiting)    # old but not 'playing'
        await _add_table(s, status="finished", age_min=300, code=finished)
        await s.commit()
        marked = await repo.abandon_idle_playing(s, _now() - timedelta(minutes=120))
        return marked, await _status_by_code(s, waiting), await _status_by_code(s, finished)

    marked, waiting_st, finished_st = _run(go)
    assert marked == 0                  # abandon only touches 'playing'
    assert waiting_st == "waiting" and finished_st == "finished"
