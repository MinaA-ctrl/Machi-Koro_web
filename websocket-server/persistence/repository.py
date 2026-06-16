"""Persistence/repository functions for the game loop (Stage 2, S2.2).

A drop-in replacement for the aiomysql functions in main.py (load/save state,
save scores, read table flags), but Postgres + async SQLAlchemy. Functions take
an AsyncSession (the FastAPI layer injects one via Depends; tests inject a test
session) — see README for the async-session pattern rationale.

Semantics preserved from the live MySQL path:
  * save_state — per-action upsert of the one game_states row (restart-safe).
  * save_scores — atomic upsert keyed on (table_id, game_seq, user_id): the QA-006
    rematch-safety property (re-finishes converge to one row per game/player; two
    games at one table under distinct game_seq both persist).
  * get_table — the (game_version, sharp, variable_supply) flags for config_for.

Not wired into the live path yet (that's the cutover, S2.6/S2.7).
"""
from __future__ import annotations

from typing import Optional

import secrets
from datetime import datetime

from sqlalchemy import and_, delete, exists, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Entitlements, GameState, Player, Score, Table, User, Wallet, WalletLedger


async def get_table(session: AsyncSession, join_code: str) -> Optional[Table]:
    """The Table row for `join_code` (carries game_version / sharp / variable_supply),
    or None."""
    result = await session.execute(select(Table).where(Table.join_code == join_code))
    return result.scalar_one_or_none()


async def load_state(session: AsyncSession, join_code: str) -> Optional[dict]:
    """The persisted engine state dict for `join_code`, or None if the table/state
    doesn't exist. JSONB round-trips back to an identical dict."""
    result = await session.execute(
        select(GameState.state)
        .join(Table, Table.id == GameState.table_id)
        .where(Table.join_code == join_code)
    )
    return result.scalar_one_or_none()


async def save_state(session: AsyncSession, join_code: str, state: dict) -> bool:
    """Persist `state` for `join_code`, overwriting the table's single game_states
    row. Awaited after every broadcasting action; a forced restart reloads the full
    game. Returns False if the table is unknown. Idempotent per (table)."""
    table = await get_table(session, join_code)
    if table is None:
        return False

    game_seq = state.get("game_seq", 0)
    stmt = pg_insert(GameState).values(
        table_id=table.id, state=state, game_seq=game_seq
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[GameState.table_id],
        set_={
            "state": stmt.excluded.state,
            "game_seq": stmt.excluded.game_seq,
            "updated_at": func.now(),
        },
    )
    await session.execute(stmt)
    await session.commit()
    return True


async def save_scores(
    session: AsyncSession,
    join_code: str,
    state: dict,
    present_user_ids: set[int] | None = None,
) -> int:
    """Persist one row per *registered* player when a finished game's state is given.
    Guests (user_id is None) are skipped. When `present_user_ids` is given, players
    who aren't in it (they left before the end) are skipped too — so a quitter doesn't
    get a history entry. Atomic + idempotent via the UNIQUE key (table_id, game_seq,
    user_id) + ON CONFLICT DO UPDATE. Returns the number of rows upserted.

    `place` (1 = winner) and `total_players` are computed from the FULL final
    standings — every player, guests included — so the place is accurate even in
    guest-heavy games."""
    table = await get_table(session, join_code)
    if table is None:
        return 0
    if state.get("phase") != "finished":
        return 0

    winner = state.get("winner")
    game_seq = state.get("game_seq", 0)
    players = state["players"]
    total_players = len(players)

    # Rank every player: winner first, then most landmarks, then most coins.
    def built(p: dict) -> int:
        return sum(1 for lm in p["landmarks"] if lm["built"] and lm["id"] != "city_hall")

    standings = sorted(
        players,
        key=lambda p: (p["seat"] != winner, -built(p), -p["coins"]),
    )
    place_by_seat = {p["seat"]: i + 1 for i, p in enumerate(standings)}

    rows = []
    for p in players:
        user_id = p.get("user_id")
        if not user_id:  # registered players only; skip guests
            continue
        if present_user_ids is not None and user_id not in present_user_ids:
            continue  # left before the end — no history entry
        rows.append(
            {
                "table_id": table.id,
                "user_id": user_id,
                "game_seq": game_seq,
                "landmarks_built": built(p),
                "coins_at_end": p["coins"],
                "won": p["seat"] == winner,
                "place": place_by_seat[p["seat"]],
                "total_players": total_players,
            }
        )
    if not rows:
        return 0

    stmt = pg_insert(Score).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Score.table_id, Score.game_seq, Score.user_id],
        set_={
            "landmarks_built": stmt.excluded.landmarks_built,
            "coins_at_end": stmt.excluded.coins_at_end,
            "won": stmt.excluded.won,
            "place": stmt.excluded.place,
            "total_players": stmt.excluded.total_players,
        },
    )
    await session.execute(stmt)
    await session.commit()
    return len(rows)


async def history_for_user(session: AsyncSession, user_id: int, limit: int = 50):
    """A registered player's finished-game history, newest first: each row plus the
    table's name and game version (for display). Tables that were deleted cascade
    their scores away, so every returned row has a live table."""
    stmt = (
        select(Score, Table.name, Table.game_version)
        .join(Table, Score.table_id == Table.id)
        .where(Score.user_id == user_id)
        .order_by(Score.played_at.desc())
        .limit(limit)
    )
    rows = await session.execute(stmt)
    return rows.all()


# ── Table / player writes (S2.3 — used by the REST surface) ──────────────────

async def generate_join_code(session: AsyncSession) -> str:
    """A unique lobby code: 'MK-' + 6 uppercase hex (mirrors mk_generate_code)."""
    while True:
        code = "MK-" + secrets.token_hex(3).upper()
        exists = await session.scalar(select(Table.id).where(Table.join_code == code))
        if not exists:
            return code


async def create_table(
    session: AsyncSession, *, name: str, is_public: bool, game_version: str,
    sharp: bool, variable_supply: bool, creator_id: str,
    password_hash: Optional[str] = None, max_players: int = 5,
) -> Table:
    table = Table(
        join_code=await generate_join_code(session),
        name=name, is_public=is_public, game_version=game_version,
        sharp=sharp, variable_supply=variable_supply, creator_id=creator_id,
        password_hash=password_hash, status="waiting", max_players=max_players,
    )
    session.add(table)
    await session.flush()  # assign table.id without ending the transaction
    return table


async def unique_display_name(
    session: AsyncSession, table_id: int, base: str, exclude_player_id: Optional[int] = None
) -> str:
    """A display name unique within the table — appends ' 1', ' 2', … on collision
    (case-insensitive), mirroring mk_unique_guest_name."""
    stmt = select(Player.display_name).where(Player.table_id == table_id)
    if exclude_player_id is not None:
        stmt = stmt.where(Player.id != exclude_player_id)
    taken = {n.lower() for n in (await session.scalars(stmt)).all()}
    candidate, i = base, 1
    while candidate.lower() in taken:
        candidate = f"{base} {i}"
        i += 1
    return candidate


async def add_player(
    session: AsyncSession, table_id: int, *, seat: int, display_name: str,
    identity: str, user_id: Optional[int] = None, is_host: bool = False,
) -> Player:
    player = Player(
        table_id=table_id, seat=seat, display_name=display_name,
        identity=identity, user_id=user_id, is_host=is_host,
    )
    session.add(player)
    await session.flush()
    return player


async def get_table_with_players(session: AsyncSession, join_code: str) -> Optional[Table]:
    """A table plus its players eagerly loaded (for the detail endpoint)."""
    result = await session.execute(
        select(Table)
        .where(Table.join_code == join_code)
        .options(selectinload(Table.players))
    )
    return result.scalar_one_or_none()


async def list_public_waiting(
    session: AsyncSession, search: str = "", waiting_cutoff: datetime | None = None
) -> list[tuple[Table, int]]:
    """Public, waiting tables whose name matches `search`, newest first, each with a
    live player count (LIMIT 50). When `waiting_cutoff` is given, stale waiting tables
    (created before it) are hidden — the lobby only shows recently-created tables."""
    stmt = (
        select(Table, func.count(Player.id))
        .outerjoin(Player, Player.table_id == Table.id)
        .where(Table.is_public.is_(True), Table.status == "waiting")
        .group_by(Table.id)
        .order_by(Table.created_at.desc())
        .limit(50)
    )
    if waiting_cutoff is not None:
        stmt = stmt.where(Table.created_at >= waiting_cutoff)
    if search:
        stmt = stmt.where(Table.name.ilike(f"%{search}%"))
    rows = await session.execute(stmt)
    return [(t, count) for t, count in rows.all()]


async def count_players(session: AsyncSession, table_id: int) -> int:
    return await session.scalar(
        select(func.count(Player.id)).where(Player.table_id == table_id)
    )


async def live_stats(session: AsyncSession, waiting_cutoff: datetime) -> tuple[int, int]:
    """(active_games, players_online): tables currently playing plus non-stale waiting
    tables, and the players seated in them. DB-derived, so it's restart-safe."""
    live = or_(
        Table.status == "playing",
        and_(Table.status == "waiting", Table.created_at >= waiting_cutoff),
    )
    games = await session.scalar(select(func.count()).select_from(Table).where(live))
    players = await session.scalar(
        select(func.count(Player.id)).join(Table, Player.table_id == Table.id).where(live)
    )
    return int(games or 0), int(players or 0)


async def next_seat(session: AsyncSession, table_id: int) -> int:
    """MAX(seat)+1 (NOT count) so a kick leaves gaps rather than reusing a live
    seat — one owner per seat (QA-004). First seat is 0."""
    max_seat = await session.scalar(
        select(func.coalesce(func.max(Player.seat), -1)).where(Player.table_id == table_id)
    )
    return max_seat + 1


async def get_player_by_seat(session: AsyncSession, table_id: int, seat: int) -> Optional[Player]:
    return await session.scalar(
        select(Player).where(Player.table_id == table_id, Player.seat == seat)
    )


async def remove_player_by_seat(session: AsyncSession, table_id: int, seat: int) -> bool:
    result = await session.execute(
        delete(Player).where(Player.table_id == table_id, Player.seat == seat)
    )
    return result.rowcount > 0


async def set_status(session: AsyncSession, table: Table, status: str) -> None:
    table.status = status
    await session.flush()


# ── Lobby lifecycle (used by the lobby WS on disconnect) ─────────────────────

async def delete_waiting_table(session: AsyncSession, join_code: str) -> bool:
    """Delete a still-waiting table (cascade removes its players). No-op once the
    game has started. Mirrors main.py's _delete_waiting_table (host left the lobby)."""
    table = await get_table(session, join_code)
    if not table or table.status != "waiting":
        return False
    await session.delete(table)
    await session.commit()
    return True


async def remove_waiting_player(session: AsyncSession, join_code: str, seat: int) -> bool:
    """Remove a player from a still-waiting table. No-op once started. Mirrors
    main.py's _remove_waiting_player (a non-host left the lobby)."""
    table = await get_table(session, join_code)
    if not table or table.status != "waiting":
        return False
    removed = await remove_player_by_seat(session, table.id, seat)
    await session.commit()
    return removed


# ── Table-lifecycle reaping (cutoff-injectable for deterministic tests) ───────

async def delete_stale_waiting(session: AsyncSession, cutoff: datetime) -> int:
    """Delete waiting tables created before `cutoff` (host never started). FK CASCADE
    removes their players/state. Returns the number deleted."""
    result = await session.execute(
        delete(Table).where(Table.status == "waiting", Table.created_at < cutoff)
    )
    await session.commit()
    return result.rowcount or 0


async def abandon_idle_playing(session: AsyncSession, cutoff: datetime) -> int:
    """Mark playing games 'abandoned' when their last activity predates `cutoff`.
    Activity = the latest game_states.updated_at (per-action save); a playing table
    with no state row yet falls back to its created_at. Returns the number marked."""
    has_stale_state = exists().where(
        GameState.table_id == Table.id, GameState.updated_at < cutoff
    )
    has_any_state = exists().where(GameState.table_id == Table.id)
    result = await session.execute(
        update(Table)
        .where(
            Table.status == "playing",
            has_stale_state | (~has_any_state & (Table.created_at < cutoff)),
        )
        .values(status="abandoned")
    )
    await session.commit()
    return result.rowcount or 0


# ── Users / accounts (S2.4 — JWT auth) ───────────────────────────────────────

async def create_user(
    session: AsyncSession, *, kind: str, display_name: str, email: Optional[str] = None,
    password_hash: Optional[str] = None, language: str = "en", avatar: Optional[str] = None,
) -> User:
    user = User(
        kind=kind, display_name=display_name, email=email,
        password_hash=password_hash, language=language, avatar=avatar,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    return await session.get(User, user_id)


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    return await session.scalar(select(User).where(User.email == email))


# ── Entitlements / wallet (S2.5 — monetization seam, free by default) ─────────

async def get_entitlements(session: AsyncSession, user_id: int) -> Optional[Entitlements]:
    """A user's entitlements row, or None — None is treated as all-free defaults."""
    return await session.get(Entitlements, user_id)


async def get_wallet(session: AsyncSession, user_id: int) -> Optional[Wallet]:
    return await session.get(Wallet, user_id)


async def adjust_wallet(session: AsyncSession, user_id: int, delta: int, reason: str) -> int:
    """STUB primitive (no economy yet, not wired to any flow): upsert the wallet and
    append a ledger row. Returns the new balance. Pricing/shop is Stages 7/8."""
    wallet = await session.get(Wallet, user_id)
    if wallet is None:
        wallet = Wallet(user_id=user_id, koro_coins=0)
        session.add(wallet)
    wallet.koro_coins += delta
    session.add(WalletLedger(user_id=user_id, delta=delta, reason=reason))
    await session.commit()
    return wallet.koro_coins
