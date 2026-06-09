"""Postgres persistence layer for the Stage-2 FastAPI backend (S2.2).

Parallel build — models, async session, repository, and Alembic migrations for the
game-data entities. Dormant: not imported by the live request path (main.py) until
the S2.6/S2.7 cutover. The MVP keeps running on WordPress + MySQL meanwhile.
"""
from .database import DATABASE_URL, async_session, database_url, engine
from .models import Base, GameState, Player, Score, Table
from .repository import get_table, load_state, save_scores, save_state

__all__ = [
    "Base",
    "Table",
    "Player",
    "GameState",
    "Score",
    "engine",
    "async_session",
    "database_url",
    "DATABASE_URL",
    "get_table",
    "load_state",
    "save_state",
    "save_scores",
]
