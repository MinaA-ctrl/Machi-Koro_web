"""SQLAlchemy 2.0 models for the game-data layer (Stage 2, S2.2).

Mirrors the live `wp_mk_*` MySQL schema (+ the sharp / variable_supply flags) for
the new FastAPI + Postgres backend. **Parallel build — not wired into the live
path yet** (the MVP keeps running on WordPress + MySQL until the S2.6/S2.7 cutover).

Users / entitlements / wallet are intentionally absent here; they arrive as their
own incremental Alembic migrations in S2.4 / S2.5.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """An account — guest or registered (S2.4). The JWT subject is
    `guest:<id>` / `user:<id>` where `<id>` is this row's id. Guests are persisted
    (kind='guest') so the no-friction flow has a stable identity and can be upgraded
    later. Registered accounts carry email + argon2 password_hash."""
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("kind IN ('guest', 'registered')", name="ck_user_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # 'guest' | 'registered'
    display_name: Mapped[str] = mapped_column(String(64))
    # Registered-only; NULL for guests. Unique among non-NULLs (Postgres lets NULLs repeat).
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, default=None)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    language: Mapped[str] = mapped_column(String(8), default="en", server_default="en")
    avatar: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Entitlements(Base):
    """Per-user host-rights + subscription state (S2.5 seam). 1:1 with users.

    **All defaults are permissive ('allowed/free') — everything is free today.** The
    shape encodes the future host-pays model so flipping defaults (or these per-user
    flags) later gates without re-architecture: Basic is always free to host;
    Harbour base and the Sharp add-on each need an entitlement, an active harbour_pass,
    or an unused one-free-host (registered-only). Free-host *consumption* is Stage 8.
    """
    __tablename__ = "entitlements"
    __table_args__ = (
        CheckConstraint("harbour_pass IN ('none', 'active')", name="ck_harbour_pass"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    # Explicit host-rights (default granted today):
    host_harbour: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    host_sharp: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # One-free-host consumables (registered-only; consumed in Stage 8). Default unused.
    free_host_harbour_used: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    free_host_sharp_used: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Subscription that grants premium hosting while active.
    harbour_pass: Mapped[str] = mapped_column(String(8), default="none", server_default="none")  # none|active
    harbour_pass_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
    ad_free: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Wallet(Base):
    """Koro Coins balance (S2.5 stub). 1:1 with users. No economy yet — balance read
    + earn/spend primitives only; pricing/shop is Stages 7/8."""
    __tablename__ = "wallets"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    koro_coins: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WalletLedger(Base):
    """Append-only Koro Coins ledger (S2.5 stub) — one row per balance change, for
    auditability once the economy exists."""
    __tablename__ = "wallet_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Table(Base):
    """A game table / room. `join_code` is the public lobby code (was wp_mk_tables.code)."""
    __tablename__ = "tables"
    __table_args__ = (
        CheckConstraint(
            "status IN ('waiting', 'playing', 'finished')", name="ck_table_status"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    join_code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    # Composed-config flags — together pick the engine config (config_for):
    game_version: Mapped[str] = mapped_column(String(16), default="harbour", server_default="harbour")
    sharp: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    variable_supply: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    # Host / creator identity (JWT subject post-S2.4; an opaque id for now).
    creator_id: Mapped[str] = mapped_column(String(64))
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    status: Mapped[str] = mapped_column(String(16), default="waiting", server_default="waiting")
    max_players: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)

    players: Mapped[list["Player"]] = relationship(
        back_populates="table", cascade="all, delete-orphan"
    )
    game_state: Mapped[Optional["GameState"]] = relationship(
        back_populates="table", cascade="all, delete-orphan", uselist=False
    )
    scores: Mapped[list["Score"]] = relationship(
        back_populates="table", cascade="all, delete-orphan"
    )


class Player(Base):
    """A seat at a table. `user_id` is NULL for guests; `display_name` carries the
    shown name (guest name today, account name once S2.4 lands)."""
    __tablename__ = "players"
    __table_args__ = (
        UniqueConstraint("table_id", "seat", name="uq_player_table_seat"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("tables.id", ondelete="CASCADE"), index=True
    )
    seat: Mapped[int] = mapped_column(Integer)
    display_name: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[Optional[int]] = mapped_column(Integer, default=None)  # NULL = guest
    # Auth principal that owns this seat: 'guest:<id>' (stand-in, S2.3) or
    # 'user:<id>' (JWT subject, S2.4). Used for seat-ownership checks (rename).
    identity: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    is_host: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    table: Mapped["Table"] = relationship(back_populates="players")


class GameState(Base):
    """The authoritative serialized engine state for a table — one row per table
    (UNIQUE table_id), overwritten per action (restart-survival)."""
    __tablename__ = "game_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("tables.id", ondelete="CASCADE"), unique=True
    )
    state: Mapped[dict] = mapped_column(JSONB)
    # Denormalized copy of state['game_seq'] for queryability (rematch discriminator).
    game_seq: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    table: Mapped["Table"] = relationship(back_populates="game_state")


class Score(Base):
    """One persisted result per (table, game, registered player). The UNIQUE key on
    (table_id, game_seq, user_id) is the QA-006 rematch-safety property: distinct
    games at one table live under distinct game_seq, and re-finishes upsert in place."""
    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint("table_id", "game_seq", "user_id", name="uq_score_table_seq_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("tables.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(Integer)  # registered players only (guests skipped)
    game_seq: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    landmarks_built: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    coins_at_end: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    won: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    table: Mapped["Table"] = relationship(back_populates="scores")
