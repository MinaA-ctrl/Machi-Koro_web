"""S2.3 REST surface, now authenticated with S2.4 JWT bearer tokens.

Each actor gets a guest JWT via /auth/guest (a stable identity reused across that
actor's requests). Covers create/join/start/list/detail/kick/rename + password
enforcement, the WEB-001 no-leak property, host/seat authorization off the JWT
subject, and the per-seat HMAC token. (GET list/detail are public, as in WP.)
"""
import base64
import hashlib
import hmac
import os


def guest_headers(client, name=None):
    """A guest JWT bearer header for one actor (stable identity across requests)."""
    body = {} if name is None else {"display_name": name}
    r = client.post("/auth/guest", json=body)
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _token_valid_for(token: str, code: str, seat: int) -> bool:
    """Recompute the per-seat WS HMAC (as the WS verifier does) — proves the token
    is bound to (code, seat) and not replayable on another seat."""
    pad = "=" * (-len(token) % 4)
    identity, exp, sig = base64.urlsafe_b64decode(token + pad).decode().rsplit("|", 2)
    msg = f"{code}|{seat}|{identity}|{exp}"
    expected = hmac.new(os.environ["MK_WS_SECRET"].encode(), msg.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def create(client, headers, **body):
    r = client.post("/tables", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ── auth required ──────────────────────────────────────────────────────────────

def test_create_requires_a_token(client):
    assert client.post("/tables", json={}).status_code == 401  # no bearer


# ── create ───────────────────────────────────────────────────────────────────

def test_create_returns_code_seat_token_and_seats_host(client):
    host = guest_headers(client)
    data = create(client, host, name="My Table", version="harbour", sharp=True, variable_supply=True)
    assert data["seat"] == 0 and data["code"].startswith("MK-")
    assert _token_valid_for(data["token"], data["code"], 0)
    assert not _token_valid_for(data["token"], data["code"], 1)  # not replayable

    detail = client.get(f"/tables/{data['code']}").json()
    assert detail["game_version"] == "harbour" and detail["sharp"] and detail["variable_supply"]
    assert len(detail["players"]) == 1 and detail["players"][0]["is_host"] is True


def test_create_defaults_and_unknown_version_falls_back(client):
    data = create(client, guest_headers(client), version="nonsense")
    detail = client.get(f"/tables/{data['code']}").json()
    assert detail["name"] == "Machi Koro Table"
    assert detail["game_version"] == "harbour"


# ── join + passwords ──────────────────────────────────────────────────────────

def test_join_increments_seat(client):
    code = create(client, guest_headers(client))["code"]
    bob = guest_headers(client)
    r = client.post(f"/tables/{code}/join", json={"guest_name": "Bob"}, headers=bob)
    assert r.status_code == 200 and r.json()["seat"] == 1
    assert _token_valid_for(r.json()["token"], code, 1)


def test_password_enforced_on_join_and_never_leaked(client):
    code = create(client, guest_headers(client), password="s3cret")["code"]
    bob = guest_headers(client)

    assert client.post(f"/tables/{code}/join", json={}, headers=bob).status_code == 403
    assert client.post(f"/tables/{code}/join", json={"password": "wrong"}, headers=bob).status_code == 403
    assert client.post(f"/tables/{code}/join", json={"password": "s3cret"}, headers=bob).status_code == 200

    detail = client.get(f"/tables/{code}").json()  # WEB-001: no secrets leaked
    assert detail["is_protected"] is True
    assert "password_hash" not in detail and "creator_id" not in detail


def test_table_full_at_max_players(client):
    code = create(client, guest_headers(client))["code"]
    for _ in range(4):
        assert client.post(f"/tables/{code}/join", json={}, headers=guest_headers(client)).status_code == 200
    assert client.post(f"/tables/{code}/join", json={}, headers=guest_headers(client)).status_code == 409


# ── start ──────────────────────────────────────────────────────────────────────

def test_start_requires_host_and_two_players(client):
    host = guest_headers(client)
    code = create(client, host)["code"]
    assert client.post(f"/tables/{code}/start", headers=host).status_code == 409  # 1 player
    bob = guest_headers(client)
    client.post(f"/tables/{code}/join", json={}, headers=bob)

    assert client.post(f"/tables/{code}/start", headers=bob).status_code == 403   # non-host
    r = client.post(f"/tables/{code}/start", headers=host)
    assert r.status_code == 200 and r.json()["started"] is True and r.json()["players"] == 2
    assert _token_valid_for(r.json()["token"], code, 0)
    assert client.get(f"/tables/{code}").json()["status"] == "playing"


# ── list + detail (public) ──────────────────────────────────────────────────────

def test_list_public_waiting_with_flags(client):
    public = create(client, guest_headers(client), name="Findable", sharp=True)["code"]
    create(client, guest_headers(client), name="Secret Room", is_public=False)
    create(client, guest_headers(client), name="Locked", password="x")

    rows = client.get("/tables", params={"search": "Find"}).json()
    assert [r["code"] for r in rows] == [public]
    assert rows[0]["player_count"] == 1 and rows[0]["sharp"] is True and rows[0]["is_protected"] is False

    by_name = {r["name"]: r for r in client.get("/tables").json()}
    assert "Secret Room" not in by_name
    assert by_name["Locked"]["is_protected"] is True


def test_detail_unknown_code_404_and_bad_code_400(client):
    assert client.get("/tables/MK-NOPEZZ").status_code == 404
    assert client.get("/tables/ab").status_code == 400


# ── kick ─────────────────────────────────────────────────────────────────────--

def test_kick_host_only_and_waiting_only(client):
    host = guest_headers(client)
    code = create(client, host)["code"]
    bob = guest_headers(client)
    client.post(f"/tables/{code}/join", json={}, headers=bob)

    assert client.post(f"/tables/{code}/kick", json={"seat": 0}, headers=bob).status_code == 403
    assert client.post(f"/tables/{code}/kick", json={"seat": 1}, headers=host).status_code == 200
    assert len(client.get(f"/tables/{code}").json()["players"]) == 1

    client.post(f"/tables/{code}/join", json={}, headers=guest_headers(client))
    client.post(f"/tables/{code}/start", headers=host)
    assert client.post(f"/tables/{code}/kick", json={"seat": 1}, headers=host).status_code == 409


# ── rename ─────────────────────────────────────────────────────────────────────

def test_rename_by_owner_and_host_but_not_others(client):
    host = guest_headers(client)
    code = create(client, host)["code"]
    bob = guest_headers(client)
    client.post(f"/tables/{code}/join", json={"guest_name": "Bob"}, headers=bob)
    eve = guest_headers(client)  # owns no seat here

    assert client.post(f"/tables/{code}/rename", json={"seat": 1, "name": "Hax"}, headers=eve).status_code == 403
    assert client.post(f"/tables/{code}/rename", json={"seat": 1, "name": "Bobby"}, headers=bob).status_code == 200
    assert client.post(f"/tables/{code}/rename", json={"seat": 1, "name": "Renamed"}, headers=host).status_code == 200

    seats = {p["seat"]: p["display_name"] for p in client.get(f"/tables/{code}").json()["players"]}
    assert seats[1] == "Renamed"


def test_duplicate_names_are_made_unique(client):
    code = create(client, guest_headers(client), guest_name="Sam")["code"]
    client.post(f"/tables/{code}/join", json={"guest_name": "Sam"}, headers=guest_headers(client))
    names = sorted(p["display_name"] for p in client.get(f"/tables/{code}").json()["players"])
    assert names == ["Sam", "Sam 1"]
