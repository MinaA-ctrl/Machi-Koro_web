"""Tables REST router (S2.3) — FastAPI reimplementation of the WP api.php surface,
on the Postgres Table/Player models + repository. Server-authoritative: host-only
kick/start and seat-ownership rename via the guest-identity stand-in; passwords
hashed (argon2) and enforced on join, never leaked.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_identity, hash_password, mint_ws_token, user_id_from, verify_password
from app.deps import clean_name, get_session, valid_code
from app.entitlements import can_host
from app.schemas import (
    CreateTableReq, CreateTableResp, JoinReq, JoinResp, KickReq, KickResp,
    PlayerOut, RenameReq, RenameResp, StartResp, TableDetail, TableListItem,
)
from persistence import repository as repo

router = APIRouter(prefix="/tables", tags=["tables"])

MAX_PLAYERS = 5
ALLOWED_VERSIONS = ("basic", "harbour")


@router.post("", response_model=CreateTableResp, status_code=201)
async def create_table(
    req: CreateTableReq,
    session: AsyncSession = Depends(get_session),
    identity: str = Depends(current_identity),
):
    name = clean_name(req.name, 40, default="Machi Koro Table")
    version = req.version.strip().lower()
    if version not in ALLOWED_VERSIONS:        # defensive fallback, like the engine
        version = "harbour"

    # Entitlements gate (S2.5). All-allow today; flipping a default later gates
    # hosting here with no re-architecture. Joining is never gated; VS is free.
    decision = await can_host(session, identity, version, req.sharp, req.variable_supply)
    if not decision.allowed:
        raise HTTPException(403, decision.reason)

    password_hash = hash_password(req.password) if req.password else None

    table = await repo.create_table(
        session, name=name, is_public=req.is_public, game_version=version,
        sharp=req.sharp, variable_supply=req.variable_supply, creator_id=identity,
        password_hash=password_hash, max_players=MAX_PLAYERS,
    )
    display = await repo.unique_display_name(
        session, table.id, clean_name(req.guest_name, 32, default="Guest")
    )
    await repo.add_player(
        session, table.id, seat=0, display_name=display, identity=identity,
        user_id=user_id_from(identity), is_host=True,
    )
    await session.commit()
    return CreateTableResp(
        code=table.join_code, seat=0, token=mint_ws_token(table.join_code, 0, identity)
    )


@router.post("/{code}/join", response_model=JoinResp)
async def join_table(
    req: JoinReq,
    code: str = Depends(valid_code),
    session: AsyncSession = Depends(get_session),
    identity: str = Depends(current_identity),
):
    table = await repo.get_table(session, code)
    if not table:
        raise HTTPException(404, "Table not found")
    if table.status != "waiting":
        raise HTTPException(409, "Game already started")
    if table.password_hash:
        if not req.password or not verify_password(req.password, table.password_hash):
            raise HTTPException(403, "Wrong password")
    if await repo.count_players(session, table.id) >= table.max_players:
        raise HTTPException(409, "Table is full")

    seat = await repo.next_seat(session, table.id)
    display = await repo.unique_display_name(
        session, table.id, clean_name(req.guest_name, 32, default="Guest")
    )
    await repo.add_player(
        session, table.id, seat=seat, display_name=display, identity=identity,
        user_id=user_id_from(identity),
    )
    await session.commit()
    return JoinResp(seat=seat, token=mint_ws_token(code, seat, identity))


@router.post("/{code}/start", response_model=StartResp)
async def start_game(
    code: str = Depends(valid_code),
    session: AsyncSession = Depends(get_session),
    identity: str = Depends(current_identity),
):
    table = await repo.get_table(session, code)
    if not table:
        raise HTTPException(404, "Table not found")
    # Host-only + waiting; one message either way so non-hosts learn nothing extra.
    if table.creator_id != identity or table.status != "waiting":
        raise HTTPException(403, "Not allowed or game already started")
    count = await repo.count_players(session, table.id)
    if count < 2:
        raise HTTPException(409, "Need at least 2 players")

    await repo.set_status(session, table, "playing")
    await session.commit()
    return StartResp(started=True, players=count, token=mint_ws_token(code, 0, identity))


@router.get("", response_model=list[TableListItem])
async def list_tables(search: str = "", session: AsyncSession = Depends(get_session)):
    rows = await repo.list_public_waiting(session, search.strip())
    return [
        TableListItem(
            code=t.join_code, name=t.name, game_version=t.game_version, sharp=t.sharp,
            variable_supply=t.variable_supply, status=t.status, is_public=t.is_public,
            player_count=count, is_protected=t.password_hash is not None,
        )
        for t, count in rows
    ]


@router.get("/{code}", response_model=TableDetail)
async def get_table_detail(
    code: str = Depends(valid_code), session: AsyncSession = Depends(get_session)
):
    table = await repo.get_table_with_players(session, code)
    if not table:
        raise HTTPException(404, "Table not found")
    players = [
        PlayerOut(seat=p.seat, display_name=p.display_name, user_id=p.user_id, is_host=p.is_host)
        for p in sorted(table.players, key=lambda p: p.seat)
    ]
    # password_hash / creator_id are absent from TableDetail — never leaked (WEB-001).
    return TableDetail(
        code=table.join_code, name=table.name, game_version=table.game_version,
        sharp=table.sharp, variable_supply=table.variable_supply, status=table.status,
        is_public=table.is_public, created_at=table.created_at,
        is_protected=table.password_hash is not None, players=players,
    )


@router.post("/{code}/kick", response_model=KickResp)
async def kick_player(
    req: KickReq,
    code: str = Depends(valid_code),
    session: AsyncSession = Depends(get_session),
    identity: str = Depends(current_identity),
):
    table = await repo.get_table(session, code)
    if not table:
        raise HTTPException(404, "Table not found")
    if table.creator_id != identity:
        raise HTTPException(403, "Only the host can kick players")
    if table.status != "waiting":  # lobby-only (PM-001): no mid-game roster edits
        raise HTTPException(409, "Can only kick before the game starts")

    if not await repo.remove_player_by_seat(session, table.id, req.seat):
        raise HTTPException(404, "No player at that seat")
    await session.commit()
    return KickResp(kicked_seat=req.seat)


@router.post("/{code}/rename", response_model=RenameResp)
async def rename_player(
    req: RenameReq,
    code: str = Depends(valid_code),
    session: AsyncSession = Depends(get_session),
    identity: str = Depends(current_identity),
):
    table = await repo.get_table(session, code)
    if not table:
        raise HTTPException(404, "Table not found")
    if table.status != "waiting":
        raise HTTPException(409, "Game already started")
    player = await repo.get_player_by_seat(session, table.id, req.seat)
    if not player:
        raise HTTPException(404, "Player not found")

    # Host, or the seat's own owner (matched via the stored identity), may rename.
    is_host = identity == table.creator_id
    is_self = player.identity is not None and identity == player.identity
    if not (is_host or is_self):
        raise HTTPException(403, "Only the host or the seat owner can rename")

    new_name = clean_name(req.name, 32)  # required
    unique = await repo.unique_display_name(
        session, table.id, new_name, exclude_player_id=player.id
    )
    player.display_name = unique
    await session.commit()
    return RenameResp(name=unique)
