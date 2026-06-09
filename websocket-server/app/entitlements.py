"""Entitlements seam (S2.5) — the host-pays gate, FREE/ALLOWED for everything today.

`can_host` consults the user's entitlements (defaults are permissive, so it allows
everything now) and encodes the future model so flipping defaults later enforces it
without re-architecture:
  * Variable Supply — a free *mode*, NEVER gated.
  * Basic base — always free to host.
  * Harbour base / Sharp add-on — each needs a host-right: an explicit entitlement,
    an active harbour_pass, or an unused one-free-host (registered-only; the actual
    free-host *consumption* is Stage 8).

Nothing here charges or consumes anything — it only reads. All free until Stage 8.
"""
from typing import NamedTuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import parse_identity
from persistence import repository as repo
from persistence.models import Entitlements


class Decision(NamedTuple):
    allowed: bool
    reason: str


def _has_host_right(ent: Entitlements | None, feature: str) -> bool:
    """Whether the user may host a premium feature ('harbour' | 'sharp'). A missing
    row → all-free default. Today the explicit flag defaults True, so this is True."""
    if ent is None:
        return True
    if getattr(ent, f"host_{feature}"):                 # explicit entitlement
        return True
    if ent.harbour_pass == "active":                    # active subscription
        return True
    if not getattr(ent, f"free_host_{feature}_used"):   # one-free-host (consumed in Stage 8)
        return True
    return False


async def can_host(
    session: AsyncSession, identity: str, version: str, sharp: bool, variable_supply: bool
) -> Decision:
    """Can `identity` host a (version, sharp, variable_supply) table? Returns
    (allowed, reason). variable_supply is intentionally never gated."""
    _, user_id = parse_identity(identity)
    ent = await repo.get_entitlements(session, user_id)

    # Basic base is always free; Harbour base needs a host-right.
    if version != "basic" and not _has_host_right(ent, "harbour"):
        return Decision(False, "harbour_host_required")
    # The Sharp add-on needs its own host-right (independent of base).
    if sharp and not _has_host_right(ent, "sharp"):
        return Decision(False, "sharp_host_required")
    # variable_supply: free mode — not consulted.
    return Decision(True, "ok")
