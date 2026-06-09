"""Async SQLAlchemy 2.0 + asyncpg engine/session setup (Stage 2, S2.2).

Mirrors the live aiomysql async style. Config via env (Postgres):
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
or a full DATABASE_URL override (normalized to the asyncpg driver).

Parallel build — not imported by the live request path (main.py) yet.
"""
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def database_url() -> str:
    """Build the asyncpg URL from env. A full DATABASE_URL wins (driver normalized)."""
    url = os.getenv("DATABASE_URL")
    if url:
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "machikoro")
    user = os.getenv("DB_USER", "machikoro")
    password = os.getenv("DB_PASSWORD", "machikoro")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = database_url()

# pool_pre_ping survives a DB restart between actions (the live game is long-lived).
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)

# expire_on_commit=False so objects stay usable after commit (we commit per action).
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
