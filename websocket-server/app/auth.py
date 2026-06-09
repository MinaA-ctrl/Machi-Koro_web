"""Auth for the Stage-2 backend (S2.4) — argon2 passwords, JWT (access + refresh),
and the per-seat game-WS token.

Identity model: the JWT **subject** is `guest:<id>` / `user:<id>` (id = users.id),
the same identity string S2.3a/b authorize on (table.creator_id, players.identity).
REST is gated by a JWT bearer dependency; the game WS is gated by the per-seat HMAC
token (the cheap socket trust anchor), which a REST endpoint mints *carrying the
verified JWT subject* — so the socket stays bound to (code, seat, identity) and
non-replayable, without decoding a JWT on the hot path.

Secrets (env, dev defaults are insecure — set real values in prod):
  MK_JWT_SECRET  — signs JWTs (HS256)
  MK_WS_SECRET   — signs the per-seat WS token (shared with the WS verifier)
"""
import base64
import hashlib
import hmac
import os
import time

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

# ── Passwords (argon2) ────────────────────────────────────────────────────────
_pwd = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(raw: str) -> str:
    return _pwd.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _pwd.verify(raw, hashed)
    except Exception:
        return False


# ── Identity subjects ─────────────────────────────────────────────────────────

def make_subject(kind: str, user_id: int) -> str:
    """users.kind + id → the JWT subject / identity string."""
    return f"{'user' if kind == 'registered' else 'guest'}:{user_id}"


def parse_identity(sub: str) -> tuple[str, int]:
    """'user:5' / 'guest:5' → ('user'|'guest', 5)."""
    prefix, _, raw = sub.partition(":")
    return prefix, int(raw)


def user_id_from(sub: str) -> int | None:
    """The users.id for a *registered* subject, else None — used to attribute scores
    (guests are not written to the scoreboard)."""
    return int(sub[len("user:"):]) if sub.startswith("user:") else None


# ── JWT (HS256, access + refresh) ─────────────────────────────────────────────
_JWT_ALG = "HS256"
ACCESS_TTL = 15 * 60            # 15 min — short-lived; refresh to extend
REFRESH_TTL = 30 * 24 * 3600    # 30 days


def _jwt_secret() -> str:
    return os.getenv("MK_JWT_SECRET", "dev-insecure-jwt-secret-change-me")


def _encode(sub: str, token_type: str, ttl: int) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": sub, "type": token_type, "iat": now, "exp": now + ttl},
        _jwt_secret(), algorithm=_JWT_ALG,
    )


def create_access_token(sub: str) -> str:
    return _encode(sub, "access", ACCESS_TTL)


def create_refresh_token(sub: str) -> str:
    return _encode(sub, "refresh", REFRESH_TTL)


def decode_token(token: str, expected_type: str) -> dict:
    """Decode + verify signature and expiry (PyJWT raises on tampered/expired), and
    require the expected token type (an access token can't be used as a refresh, etc.)."""
    payload = jwt.decode(token, _jwt_secret(), algorithms=[_JWT_ALG])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("wrong token type")
    return payload


_bearer = HTTPBearer(auto_error=False)


def current_identity(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    """Bearer-JWT dependency → the verified subject (`guest:<id>` / `user:<id>`).
    Replaces the S2.3 X-MK-Guest header. 401 on missing/invalid/expired access token."""
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(creds.credentials, "access")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    sub = payload.get("sub", "")
    if not (sub.startswith("user:") or sub.startswith("guest:")):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    return sub


# ── Per-seat game-WS token (HMAC; the socket trust anchor) ────────────────────
WS_TOKEN_TTL = 6 * 3600  # 6h — covers lobby wait + a full game


def _ws_secret() -> str:
    return os.getenv("MK_WS_SECRET", "")


def mint_ws_token(code: str, seat: int, identity: str, ttl: int = WS_TOKEN_TTL) -> str:
    """Issue a per-seat game-WS token carrying the (JWT-derived) `identity`. Wire
    format base64url(identity|exp|sig), sig = HMAC-SHA256(code|seat|identity|exp).
    `seat` is signed, so a token can't be replayed on another seat. Minted only by
    an authenticated REST endpoint. Empty string if no secret is configured."""
    secret = _ws_secret()
    if not secret:
        return ""
    exp = int(time.time()) + ttl
    msg = f"{code}|{seat}|{identity}|{exp}"
    sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    plain = f"{identity}|{exp}|{sig}"
    return base64.urlsafe_b64encode(plain.encode()).decode().rstrip("=")


def verify_ws_token(token: str, code: str, seat: int) -> bool:
    """Verify a per-seat game token (inverse of mint_ws_token). Recomputes
    HMAC-SHA256 over code|seat|identity|exp, where identity is the JWT subject the
    minting REST call authenticated. `seat` is signed → not replayable across seats.
    False on any malformed/expired/mismatched token, or if no secret is configured."""
    secret = _ws_secret()
    if not secret or not token:
        return False
    try:
        pad = "=" * (-len(token) % 4)
        identity, exp_str, sig = base64.urlsafe_b64decode(token + pad).decode().rsplit("|", 2)
        exp = int(exp_str)
    except Exception:
        return False
    if exp < time.time():
        return False
    msg = f"{code}|{seat}|{identity}|{exp}"
    expected = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
