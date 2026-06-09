"""Fixtures for the persistence suite (S2.2).

Runs against a live Postgres with the Alembic baseline already applied (CI runs
`alembic upgrade head` first). Each test starts clean (TRUNCATE … CASCADE).

Why a per-test engine with NullPool: pytest-asyncio gives each test its own event
loop, but the app's module-level async engine binds its pool to the first loop it
touches — reusing it across tests raises "attached to a different loop". A fresh
NullPool engine per test (created/disposed inside the test's loop) sidesteps that.
The production `persistence.database.engine` is unaffected (one app loop).
"""
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from persistence.database import DATABASE_URL


@pytest_asyncio.fixture
async def db_engine():
    eng = create_async_engine(DATABASE_URL, poolclass=NullPool)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine):
    """A sessionmaker on the per-test engine — use it to open additional sessions
    (e.g. to simulate a backend restart reloading state)."""
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def clean_db(db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE scores, game_states, players, tables RESTART IDENTITY CASCADE")
        )
    yield


@pytest_asyncio.fixture
async def session(session_factory):
    async with session_factory() as s:
        yield s
