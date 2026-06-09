"""S2.4 — JWT auth + accounts: register/login/refresh/me, guest flow, JWT verify
(expired/tampered/missing rejected), per-seat WS auth derived from a JWT identity,
and host/seat authorization off the JWT subject.
"""
import pytest
from fastapi import WebSocketDisconnect

from app.auth import _encode  # craft an expired token deterministically


def bearer(token_resp: dict) -> dict:
    return {"Authorization": f"Bearer {token_resp['access_token']}"}


def register(client, email, password="password123", **extra):
    return client.post("/auth/register", json={"email": email, "password": password, **extra})


# ── register / login / me ──────────────────────────────────────────────────────

def test_register_login_me_and_no_password_leak(client):
    r = register(client, "alice@example.com", display_name="Alice")
    assert r.status_code == 201 and r.json()["token_type"] == "bearer"

    me = client.get("/auth/me", headers=bearer(r.json())).json()
    assert me["kind"] == "registered" and me["email"] == "alice@example.com" and me["display_name"] == "Alice"
    assert "password_hash" not in me

    assert register(client, "alice@example.com").status_code == 409          # duplicate email
    assert client.post("/auth/login", json={"email": "alice@example.com", "password": "password123"}).status_code == 200
    assert client.post("/auth/login", json={"email": "alice@example.com", "password": "nope"}).status_code == 401
    assert client.post("/auth/login", json={"email": "ghost@example.com", "password": "x"}).status_code == 401


# ── guest flow (first-class) ────────────────────────────────────────────────────

def test_guest_flow(client):
    r = client.post("/auth/guest", json={"display_name": "Gus"})
    assert r.status_code == 201
    me = client.get("/auth/me", headers=bearer(r.json())).json()
    assert me["kind"] == "guest" and me["email"] is None and me["display_name"] == "Gus"


# ── refresh ──────────────────────────────────────────────────────────────────---

def test_refresh_rotates_and_rejects_access_token(client):
    issued = client.post("/auth/guest", json={}).json()
    rotated = client.post("/auth/refresh", json={"refresh_token": issued["refresh_token"]})
    assert rotated.status_code == 200 and rotated.json()["access_token"]
    # an access token is not a refresh token (type enforced)
    assert client.post("/auth/refresh", json={"refresh_token": issued["access_token"]}).status_code == 401


# ── JWT verification: expired / tampered / missing ──────────────────────────────

def test_jwt_expired_tampered_and_missing_rejected(client):
    expired = _encode("guest:1", "access", -10)  # already expired
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401

    good = client.post("/auth/guest", json={}).json()["access_token"]
    tampered = good[:-2] + ("ab" if good[-2:] != "ab" else "cd")  # break the signature
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401

    assert client.get("/auth/me").status_code == 401  # missing bearer


# ── per-seat WS auth derived from the JWT identity ──────────────────────────────

def test_per_seat_ws_auth_on_jwt_identity(client):
    host = bearer(register(client, "host@example.com").json())
    code = client.post("/tables", json={}, headers=host).json()["code"]
    bob = bearer(client.post("/auth/guest", json={}).json())
    client.post(f"/tables/{code}/join", json={}, headers=bob)
    start_tok = client.post(f"/tables/{code}/start", headers=host).json()["token"]  # seat 0

    # The JWT-derived per-seat token authorizes the game socket for its seat…
    with client.websocket_connect(f"/ws/{code}/game/0?token={start_tok}") as ws:
        assert ws.receive_json()["event"] == "state_update"

    # …but is not replayable on another seat (impersonation → 4401).
    with client.websocket_connect(f"/ws/{code}/game/1?token={start_tok}") as ws:
        with pytest.raises(WebSocketDisconnect) as ei:
            ws.receive_json()
    assert ei.value.code == 4401


# ── host/seat authorization off the JWT subject ─────────────────────────────────

def test_host_authz_off_jwt_subject(client):
    host = bearer(register(client, "owner@example.com").json())
    code = client.post("/tables", json={}, headers=host).json()["code"]
    bob = bearer(client.post("/auth/guest", json={}).json())
    client.post(f"/tables/{code}/join", json={}, headers=bob)

    assert client.post(f"/tables/{code}/start", headers=bob).status_code == 403   # non-host (guest)
    assert client.post(f"/tables/{code}/start", headers=host).status_code == 200  # host (registered)
