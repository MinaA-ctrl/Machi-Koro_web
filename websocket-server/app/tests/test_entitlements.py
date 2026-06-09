"""S2.5 — entitlements seam (free by default) + wallet stub.

Proves the gate is live (a forced-deny entitlement → create 403) while everything
is allowed today, join is never gated, and Variable Supply is never gated.
"""
import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app import wallet
from app.entitlements import can_host
from persistence.database import DATABASE_URL
from persistence.models import Entitlements


def _run(fn):
    """Run an async fn(session) on a throwaway loop (separate from the TestClient
    portal loop), NullPool engine disposed each call."""
    async def _wrap():
        eng = create_async_engine(DATABASE_URL, poolclass=NullPool)
        sm = async_sessionmaker(eng, expire_on_commit=False)
        try:
            async with sm() as s:
                return await fn(s)
        finally:
            await eng.dispose()
    return asyncio.run(_wrap())


def reg(client, email):
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def gst(client):
    r = client.post("/auth/guest", json={})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def uid_of(client, headers):
    return client.get("/auth/me", headers=headers).json()["id"]


def seed_entitlements(user_id, **flags):
    async def _seed(s):
        s.add(Entitlements(user_id=user_id, **flags))
        await s.commit()
    _run(_seed)


# ── all-allow today ────────────────────────────────────────────────────────────

def test_create_all_allowed_for_default_users(client):
    # Registered and guest, no entitlements row → everything hosts (incl. Sharp + VS).
    for headers in (reg(client, "free@example.com"), gst(client)):
        r = client.post("/tables", json={"version": "harbour", "sharp": True, "variable_supply": True},
                        headers=headers)
        assert r.status_code == 201, r.text


def test_can_host_service_all_allow_and_vs_ignored(client):
    gid = uid_of(client, gst(client))
    ident = f"guest:{gid}"
    for version, sharp, vs in [("harbour", True, True), ("basic", True, False), ("harbour", False, True)]:
        d = _run(lambda s, v=version, sp=sharp, x=vs: can_host(s, ident, v, sp, x))
        assert d.allowed and d.reason == "ok"


# ── forced deny proves the gate works (flip a default later → gated) ──────────-

def test_forced_deny_harbour_gates_create_but_basic_is_free(client):
    h = reg(client, "denyharbour@example.com")
    seed_entitlements(uid_of(client, h), host_harbour=False, free_host_harbour_used=True)
    # Harbour host-right denied → 403; Basic is always free → 201.
    assert client.post("/tables", json={"version": "harbour"}, headers=h).status_code == 403
    assert client.post("/tables", json={"version": "basic"}, headers=h).status_code == 201


def test_forced_deny_sharp_gates_even_on_basic_base(client):
    h = reg(client, "denysharp@example.com")
    seed_entitlements(uid_of(client, h), host_sharp=False, free_host_sharp_used=True)
    # Sharp add-on denied regardless of base.
    assert client.post("/tables", json={"version": "basic", "sharp": True}, headers=h).status_code == 403
    assert client.post("/tables", json={"version": "basic", "sharp": False}, headers=h).status_code == 201


def test_active_harbour_pass_overrides_denied_flag(client):
    h = reg(client, "subscriber@example.com")
    # explicit right off + free-host used, but an active subscription grants hosting.
    seed_entitlements(uid_of(client, h), host_harbour=False, free_host_harbour_used=True,
                      harbour_pass="active")
    assert client.post("/tables", json={"version": "harbour"}, headers=h).status_code == 201


# ── join never gated; VS never gated ──────────────────────────────────────────

def test_join_is_never_gated(client):
    host = reg(client, "host@example.com")
    code = client.post("/tables", json={"version": "harbour"}, headers=host).json()["code"]
    # A user who may NOT host Harbour can still join one.
    joiner = reg(client, "cantHost@example.com")
    seed_entitlements(uid_of(client, joiner), host_harbour=False, free_host_harbour_used=True)
    assert client.post(f"/tables/{code}/join", json={}, headers=joiner).status_code == 200


def test_variable_supply_is_never_gated(client):
    h = reg(client, "vsuser@example.com")
    seed_entitlements(uid_of(client, h), host_harbour=False, free_host_harbour_used=True)
    # Basic + VS is fine even when Harbour hosting is denied (VS is a free mode)…
    assert client.post("/tables", json={"version": "basic", "variable_supply": True}, headers=h).status_code == 201
    # …and when Harbour itself is denied, the denial is Harbour, never VS.
    r = client.post("/tables", json={"version": "harbour", "variable_supply": True}, headers=h)
    assert r.status_code == 403 and r.json()["detail"] == "harbour_host_required"


# ── wallet stub ────────────────────────────────────────────────────────────────

def test_wallet_balance_and_stub_earn_spend(client):
    gid = uid_of(client, gst(client))
    ident = f"guest:{gid}"
    assert _run(lambda s: wallet.get_balance(s, ident)) == 0          # default
    assert _run(lambda s: wallet.earn(s, ident, 50, "test")) == 50
    assert _run(lambda s: wallet.get_balance(s, ident)) == 50         # persisted
    assert _run(lambda s: wallet.spend(s, ident, 20, "test")) == 30
    assert _run(lambda s: wallet.spend(s, ident, 1000, "test")) is None  # no overdraft
