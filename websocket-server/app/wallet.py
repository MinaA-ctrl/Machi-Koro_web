"""Koro Coins wallet — STUB (S2.5). Balance read + earn/spend primitives, no
economy yet: nothing here is wired to pricing or any game flow (that's Stages 7/8).
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import parse_identity
from persistence import repository as repo


async def get_balance(session: AsyncSession, identity: str) -> int:
    """Current Koro Coins balance (0 if the user has no wallet row yet)."""
    _, user_id = parse_identity(identity)
    wallet = await repo.get_wallet(session, user_id)
    return wallet.koro_coins if wallet else 0


async def earn(session: AsyncSession, identity: str, amount: int, reason: str = "earn") -> int:
    """STUB grant — not wired to any flow. Returns the new balance."""
    _, user_id = parse_identity(identity)
    return await repo.adjust_wallet(session, user_id, abs(amount), reason)


async def spend(session: AsyncSession, identity: str, amount: int, reason: str = "spend") -> int | None:
    """STUB spend — not wired to any flow. Returns the new balance, or None if the
    balance is insufficient (no overdraft)."""
    if await get_balance(session, identity) < amount:
        return None
    _, user_id = parse_identity(identity)
    return await repo.adjust_wallet(session, user_id, -abs(amount), reason)
