"""Phase 0 — lobby WebSocket security.

The lobby socket is gated like the game socket (per-seat token whose identity still
owns the seat), only relays a small whitelist of client hints with the sender's seat
stamped by the server, and keeps kick/start host-only.
"""
import pytest
from fastapi import WebSocketDisconnect
from sqlalchemy import select

from app.auth import mint_ws_token
from app.tests.test_ws_game import _code, _run, connect, seed_started
from app.ws import MAX_CLIENT_MESSAGE_BYTES
from persistence.models import Player, Table


def seed_waiting(code, players):
    """Insert a waiting table + players. `players` = [(seat, identity)]."""
    async def _seed(s):
        t = Table(join_code=code, name="T", creator_id=players[0][1], status="waiting",
                  game_version="harbour")
        s.add(t)
        await s.flush()
        for seat, identity in players:
            s.add(Player(table_id=t.id, seat=seat, display_name=f"P{seat}",
                         identity=identity, is_host=(seat == 0)))
        await s.commit()
    _run(_seed)


def table_exists(code):
    async def _q(s):
        return await s.scalar(select(Table.id).where(Table.join_code == code)) is not None
    return _run(_q)


def lobby(client, code, seat, identity, token=None):
    tok = token if token is not None else mint_ws_token(code, seat, identity)
    return client.websocket_connect(f"/ws/{code}/lobby/{seat}?token={tok}")


def assert_rejected(ws_ctx):
    with ws_ctx as ws:
        with pytest.raises(WebSocketDisconnect) as ei:
            ws.receive_json()
    assert ei.value.code == 4401


HOST, GUEST = "user:10", "guest:20"


def test_lobby_rejects_missing_bad_and_wrong_seat_tokens(client):
    code = _code()
    seed_waiting(code, [(0, HOST), (1, GUEST)])
    assert_rejected(lobby(client, code, 0, HOST, token=""))
    assert_rejected(lobby(client, code, 0, HOST, token="garbage"))
    # A guest's seat-1 token replayed on the host seat.
    assert_rejected(client.websocket_connect(
        f"/ws/{code}/lobby/0?token={mint_ws_token(code, 1, GUEST)}"))
    assert table_exists(code)  # the failed host-seat attempt did not close the table


def test_stale_token_of_former_seat_owner_is_rejected(client):
    """A validly signed token whose identity no longer owns the seat (kicked, seat
    reassigned) is refused on both the lobby and the game socket."""
    code = _code()
    seed_waiting(code, [(0, HOST), (1, GUEST)])
    assert_rejected(lobby(client, code, 1, "guest:99"))

    started = _code()
    seed_started(started, players=[(0, "A", 10), (1, "B", 20)])
    assert_rejected(connect(client, started, 1, identity="guest:99"))


def test_only_whitelisted_events_relayed_with_server_stamped_seat(client):
    code = _code()
    seed_waiting(code, [(0, HOST), (1, GUEST)])
    with lobby(client, code, 0, HOST) as host:
        assert host.receive_json() == {"event": "player_joined", "seat": "0"}
        with lobby(client, code, 1, GUEST) as guest:
            assert host.receive_json() == {"event": "player_joined", "seat": "1"}
            guest.receive_json()

            guest.send_json({"event": "player_kicked", "seat": 0})   # not the host
            guest.send_json({"event": "game_started"})               # not the host
            guest.send_json({"event": "table_closed"})               # not client-sendable
            guest.send_json({"event": "player_renamed", "seat": 0})  # claims seat 0
            # Only the rename arrives, attributed to the real sender.
            assert host.receive_json() == {"event": "player_renamed", "seat": "1"}

            assert guest.receive_json() == {"event": "player_renamed", "seat": "1"}  # own echo
            host.send_json({"event": "player_kicked", "seat": 1})
            assert guest.receive_json() == {"event": "player_kicked", "seat": "1"}


def test_bad_frames_are_ignored_without_dropping_the_socket(client):
    code = _code()
    seed_waiting(code, [(0, HOST)])
    with lobby(client, code, 0, HOST) as host:
        host.receive_json()
        host.send_text("{not json")
        host.send_text("[1, 2, 3]")
        host.send_text('{"event": "player_renamed", "pad": "' + "x" * MAX_CLIENT_MESSAGE_BYTES + '"}')
        host.send_json({"event": "player_kicked", "seat": "1"})  # seat must be an int
        host.send_json({"event": "player_renamed"})
        assert host.receive_json() == {"event": "player_renamed", "seat": "0"}


def test_replaced_host_socket_does_not_close_the_table(client):
    """A reload/second tab replaces the host's socket; the old one closing must not
    be treated as the host leaving."""
    code = _code()
    seed_waiting(code, [(0, HOST)])
    with lobby(client, code, 0, HOST) as first:
        first.receive_json()
        with lobby(client, code, 0, HOST) as second:
            second.receive_json()
            first.close()
            second.send_json({"event": "player_renamed"})
            assert second.receive_json() == {"event": "player_renamed", "seat": "0"}
            assert table_exists(code)
