"""Request-scoped dependencies + input validation for the FastAPI app (S2.3)."""
import re
from collections.abc import AsyncIterator

from fastapi import HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from persistence.database import async_session

_CODE_RE = re.compile(r"^[A-Z0-9\-]{3,12}$")


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession per request. Endpoints own the transaction (commit
    after their writes); the session is closed on exit."""
    async with async_session() as session:
        yield session


def valid_code(code: str = Path(...)) -> str:
    """Normalize + validate a table code (mirrors mk_validate_code): uppercased,
    `^[A-Z0-9-]{3,12}$`, else 400."""
    c = (code or "").strip().upper()
    if not _CODE_RE.match(c):
        raise HTTPException(status_code=400, detail="Invalid table code")
    return c


def clean_name(raw: str | None, max_len: int, default: str | None = None) -> str:
    """Trim + length-clamp a name (mirrors mk_validate_name). Falls back to
    `default` when blank if given, else 400."""
    name = (raw or "").strip()
    if not name:
        if default is not None:
            return default
        raise HTTPException(status_code=400, detail="Name is required")
    return name[:max_len]
