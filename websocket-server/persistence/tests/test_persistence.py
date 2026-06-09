"""Persistence layer tests (S2.2) — run against a migrated Postgres.

Covers the acceptance criteria: migrations applied (schema present), game_states
per-action round-trip / restart-survival, and scores rematch-safety (the UNIQUE
(table_id, game_seq, user_id) key).
"""
from sqlalchemy import func, inspect, select

from machi_koro_engine import create_initial_state, config_for
from persistence.models import GameState, Score, Table
from persistence.repository import get_table, load_state, save_scores, save_state


# ── helpers ──────────────────────────────────────────────────────────────────

async def _make_table(session, join_code="MK-TEST", **kw):
    t = Table(join_code=join_code, name="Test Table", creator_id="user:1", **kw)
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t


def _finished_state(game_seq=0, winner=0):
    """A minimal finished state: seat 0 (user 10) won with 1 landmark; seat 1
    (user 20) lost with 0; plus a guest (no user_id) who must be skipped."""
    return {
        "phase": "finished",
        "winner": winner,
        "game_seq": game_seq,
        "players": [
            {"seat": 0, "user_id": 10, "coins": 7,
             "landmarks": [{"id": "train_station", "built": True},
                           {"id": "city_hall", "built": True}]},
            {"seat": 1, "user_id": 20, "coins": 3,
             "landmarks": [{"id": "train_station", "built": False},
                           {"id": "city_hall", "built": True}]},
            {"seat": 2, "user_id": None, "coins": 5,  # guest — skipped
             "landmarks": [{"id": "train_station", "built": True}]},
        ],
    }


async def _count_scores(session, user_id):
    res = await session.execute(
        select(func.count()).select_from(Score).where(Score.user_id == user_id)
    )
    return res.scalar_one()


# ── migrations applied ─────────────────────────────────────────────────────--

async def test_schema_present_after_migration(db_engine):
    async with db_engine.connect() as conn:
        names = await conn.run_sync(lambda c: inspect(c).get_table_names())
    assert {"tables", "players", "game_states", "scores"} <= set(names)
    assert "alembic_version" in names  # alembic upgrade head ran


# ── get_table flags ─────────────────────────────────────────────────────────-

async def test_get_table_returns_flags(session):
    await _make_table(session, join_code="MK-FLAGS",
                      game_version="harbour", sharp=True, variable_supply=True)
    t = await get_table(session, "MK-FLAGS")
    assert t is not None
    assert (t.game_version, t.sharp, t.variable_supply) == ("harbour", True, True)
    # and the flags resolve to the composed engine config
    cfg = config_for(t.game_version, t.sharp, t.variable_supply)
    assert cfg.name == "Harbour + Sharp" and cfg.variable_supply is True

    assert await get_table(session, "NOPE") is None


# ── game_states round-trip / restart survival ─────────────────────────────────

async def test_game_state_roundtrip_identical(session, session_factory):
    await _make_table(session, join_code="MK-RT")
    state = create_initial_state(
        [{"seat": 0, "display_name": "A"}, {"seat": 1, "display_name": "B"}],
        config=config_for("harbour", True, True),  # Sharp + Variable Supply (deck present)
    )
    assert await save_state(session, "MK-RT", state) is True

    # Reload through a brand-new session — simulates a backend restart.
    async with session_factory() as fresh:
        reloaded = await load_state(fresh, "MK-RT")
    assert reloaded == state  # JSONB round-trips identical


async def test_save_state_is_per_action_upsert(session, session_factory):
    await _make_table(session, join_code="MK-UP")
    await save_state(session, "MK-UP", {"phase": "roll", "game_seq": 0, "n": 1})
    await save_state(session, "MK-UP", {"phase": "build", "game_seq": 0, "n": 2})
    # Exactly one row per table; latest write wins.
    res = await session.execute(select(func.count()).select_from(GameState))
    assert res.scalar_one() == 1
    async with session_factory() as fresh:
        assert (await load_state(fresh, "MK-UP"))["n"] == 2


async def test_save_state_unknown_table_returns_false(session):
    assert await save_state(session, "GHOST", {"phase": "roll"}) is False


# ── scores rematch-safety (the QA-006 UNIQUE key) ─────────────────────────────

async def test_scores_skip_guests_and_record_winner(session):
    await _make_table(session, join_code="MK-S1")
    n = await save_scores(session, "MK-S1", _finished_state(game_seq=0, winner=0))
    assert n == 2  # two registered players; the guest was skipped

    rows = (await session.execute(select(Score).order_by(Score.user_id))).scalars().all()
    assert [r.user_id for r in rows] == [10, 20]
    winner_row = next(r for r in rows if r.user_id == 10)
    assert winner_row.won is True and winner_row.landmarks_built == 1 and winner_row.coins_at_end == 7
    loser_row = next(r for r in rows if r.user_id == 20)
    assert loser_row.won is False and loser_row.landmarks_built == 0


async def test_scores_refinish_is_idempotent(session):
    await _make_table(session, join_code="MK-S2")
    st = _finished_state(game_seq=0, winner=0)
    await save_scores(session, "MK-S2", st)
    await save_scores(session, "MK-S2", st)  # re-finish / duplicate write
    # Still exactly one row per (table, game_seq, user) — the UNIQUE key holds.
    assert await _count_scores(session, 10) == 1
    assert await _count_scores(session, 20) == 1


async def test_scores_rematch_distinct_game_seq_both_persist(session):
    await _make_table(session, join_code="MK-S3")
    await save_scores(session, "MK-S3", _finished_state(game_seq=0, winner=0))
    await save_scores(session, "MK-S3", _finished_state(game_seq=1, winner=1))
    # Two games at one table → two rows per user, one per game_seq (QA-006).
    assert await _count_scores(session, 10) == 2
    assert await _count_scores(session, 20) == 2
    total = (await session.execute(select(func.count()).select_from(Score))).scalar_one()
    assert total == 4

    # game 2's winner flipped to seat 1 (user 20); each game keeps its own result.
    g2_winner = await session.execute(
        select(Score.won).where(Score.user_id == 20, Score.game_seq == 1)
    )
    assert g2_winner.scalar_one() is True
