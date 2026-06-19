"""Auth router (S2.4) — register / login / guest / refresh / me.

Issues JWT (access + refresh) whose subject is the account identity
(`guest:<id>` / `user:<id>`). Guests are first-class: /auth/guest issues a guest
JWT so the no-friction flow is preserved. Passwords are argon2-hashed and never
returned.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token, create_refresh_token, current_identity, decode_token,
    hash_password, make_subject, parse_identity, verify_password,
)
from app.deps import clean_name, get_session
from app.ratelimit import auth_limit
from app.schemas import (
    GuestReq, LoginReq, RefreshReq, RegisterReq, ScoreHistoryItem, TokenPair, UserOut,
    UserStats,
)
from persistence import repository as repo

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens(subject: str) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


def _user_out(user) -> UserOut:
    return UserOut(
        id=user.id, kind=user.kind, display_name=user.display_name,
        email=user.email, language=user.language, avatar=user.avatar,
    )


@router.post("/register", response_model=TokenPair, status_code=201, dependencies=[Depends(auth_limit)])
async def register(req: RegisterReq, session: AsyncSession = Depends(get_session)):
    # One account per email (exact match — different casing can be a different mail).
    if await repo.get_user_by_email(session, req.email):
        raise HTTPException(409, "Email already registered")
    # Registered display names must be unique (two people can't share a name). If the
    # user TYPED a name that's taken, ask them to change it ("name_taken"); if the name
    # was auto-derived from their email and happens to clash, silently disambiguate so
    # registration still succeeds.
    provided = bool((req.display_name or "").strip())
    display = clean_name(req.display_name, 64, default=req.email.split("@")[0])
    if await repo.registered_display_name_taken(session, display):
        if provided:
            raise HTTPException(409, "name_taken")
        base, n = display, 2
        while await repo.registered_display_name_taken(session, display):
            display = f"{base}{n}"[:64]
            n += 1
    user = await repo.create_user(
        session, kind="registered", display_name=display, email=req.email,
        password_hash=hash_password(req.password), language=req.language,
    )
    return _tokens(make_subject("registered", user.id))


@router.post("/login", response_model=TokenPair, dependencies=[Depends(auth_limit)])
async def login(req: LoginReq, session: AsyncSession = Depends(get_session)):
    user = await repo.get_user_by_email(session, req.email)
    # Same error whether the email is unknown or the password is wrong (no enumeration).
    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return _tokens(make_subject("registered", user.id))


@router.post("/guest", response_model=TokenPair, status_code=201, dependencies=[Depends(auth_limit)])
async def guest(req: GuestReq, session: AsyncSession = Depends(get_session)):
    display = clean_name(req.display_name, 64, default="Guest")
    user = await repo.create_user(session, kind="guest", display_name=display, language=req.language)
    return _tokens(make_subject("guest", user.id))


@router.post("/refresh", response_model=TokenPair)
async def refresh(req: RefreshReq):
    try:
        payload = decode_token(req.refresh_token, "refresh")
    except Exception:
        raise HTTPException(401, "Invalid or expired refresh token")
    sub = payload.get("sub", "")
    if not (sub.startswith("user:") or sub.startswith("guest:")):
        raise HTTPException(401, "Invalid token subject")
    return _tokens(sub)  # rotate: fresh access + refresh


@router.get("/me", response_model=UserOut)
async def me(
    identity: str = Depends(current_identity), session: AsyncSession = Depends(get_session)
):
    _, user_id = parse_identity(identity)
    user = await repo.get_user(session, user_id)
    if not user:
        raise HTTPException(404, "Account not found")
    return _user_out(user)


@router.get("/me/history", response_model=list[ScoreHistoryItem])
async def my_history(
    identity: str = Depends(current_identity), session: AsyncSession = Depends(get_session)
):
    """Finished-game history for the signed-in registered player. Guests have none."""
    kind, user_id = parse_identity(identity)
    if kind != "user":
        return []
    rows = await repo.history_for_user(session, user_id)
    return [
        ScoreHistoryItem(
            table_name=name,
            game_version=version,
            place=score.place,
            total_players=score.total_players,
            won=score.won,
            landmarks_built=score.landmarks_built,
            coins_at_end=score.coins_at_end,
            points=score.points,
            played_at=score.played_at,
        )
        for score, name, version in rows
    ]


@router.get("/me/stats", response_model=UserStats)
async def my_stats(
    identity: str = Depends(current_identity), session: AsyncSession = Depends(get_session)
):
    """Lifetime point total + games played/won for the signed-in registered player.
    Guests have no stats (all zeros)."""
    kind, user_id = parse_identity(identity)
    if kind != "user":
        return UserStats()
    return UserStats(**await repo.stats_for_user(session, user_id))
