"""Fixtures for the app/API suite (S2.3).

A single session-scoped TestClient drives the async app on one persistent portal
loop, so the module-level async engine binds once and is reused across all tests
(separate per-test TestClients would each open a new loop and clash with the shared
engine's pool). Identity is a JWT bearer token (S2.4), obtained via /auth/guest or
/auth/register per actor.

Each test starts from a clean DB. Needs a live Postgres with the Alembic
migrations applied (the `backend-tests` CI job runs `alembic upgrade head` first).
"""
import asyncio
import os

import pytest

# Deterministic secrets so per-seat WS tokens and JWTs are mintable/verifiable.
os.environ.setdefault("MK_WS_SECRET", "test-secret")
os.environ.setdefault("MK_JWT_SECRET", "test-jwt-secret")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.main import app  # noqa: E402
from persistence.database import DATABASE_URL  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:  # context-managed → one portal loop for the session
        yield c


@pytest.fixture(autouse=True)
def clean_db():
    # Own short-lived NullPool engine on a throwaway loop — never touches the app's
    # module engine (which stays bound to the TestClient portal loop).
    async def _truncate():
        eng = create_async_engine(DATABASE_URL, poolclass=NullPool)
        async with eng.begin() as conn:
            await conn.execute(
                text("TRUNCATE scores, game_states, players, tables, "
                     "wallet_ledger, wallets, entitlements, users RESTART IDENTITY CASCADE")
            )
        await eng.dispose()

    asyncio.run(_truncate())
    yield
