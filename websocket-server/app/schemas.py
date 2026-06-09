"""Pydantic v2 request/response models for the tables REST surface (S2.3).

Response models list only safe fields — `password_hash` and `creator_id` are never
included, preserving the WEB-001 no-leak property by construction.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ── auth (S2.4) ────────────────────────────────────────────────────────────────

class RegisterReq(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = None
    language: str = "en"


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class GuestReq(BaseModel):
    display_name: str | None = None
    language: str = "en"


class RefreshReq(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    kind: str
    display_name: str
    email: str | None
    language: str
    avatar: str | None


# ── requests ─────────────────────────────────────────────────────────────────

class CreateTableReq(BaseModel):
    name: str | None = None                 # blank → "Machi Koro Table"
    is_public: bool = True
    guest_name: str | None = None           # blank → "Guest"
    version: str = "harbour"                # 'basic' | 'harbour'; unknown → harbour
    sharp: bool = False
    variable_supply: bool = False
    password: str | None = None             # optional; hashed if present


class JoinReq(BaseModel):
    guest_name: str | None = None
    password: str | None = None


class KickReq(BaseModel):
    seat: int = Field(ge=0)


class RenameReq(BaseModel):
    seat: int = Field(ge=0)
    name: str


# ── responses ────────────────────────────────────────────────────────────────

class CreateTableResp(BaseModel):
    code: str
    seat: int
    token: str


class JoinResp(BaseModel):
    seat: int
    token: str


class StartResp(BaseModel):
    started: bool
    players: int
    token: str


class PlayerOut(BaseModel):
    seat: int
    display_name: str
    user_id: int | None
    is_host: bool


class TableListItem(BaseModel):
    code: str
    name: str
    game_version: str
    sharp: bool
    variable_supply: bool
    status: str
    is_public: bool
    player_count: int
    is_protected: bool


class TableDetail(BaseModel):
    code: str
    name: str
    game_version: str
    sharp: bool
    variable_supply: bool
    status: str
    is_public: bool
    created_at: datetime
    is_protected: bool
    players: list[PlayerOut]


class KickResp(BaseModel):
    kicked_seat: int


class RenameResp(BaseModel):
    name: str
