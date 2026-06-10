"""S2.6a — cutover security gates: rate limiting (active + test bypass) and the
prod-secret boot guard.
"""
import pytest

from app import ratelimit
from app.config import require_secrets


# ── rate limiting ──────────────────────────────────────────────────────────────

def test_rate_limiting_off_by_default(client):
    # Default (no MK_RATE_LIMIT / MK_ENV) → not throttled (the test-mode bypass).
    codes = [client.post("/auth/guest", json={}).status_code for _ in range(15)]
    assert codes == [201] * 15


def test_rate_limiting_active_when_enabled(client, monkeypatch):
    monkeypatch.setenv("MK_RATE_LIMIT", "on")
    ratelimit.reset()
    try:
        codes = [client.post("/auth/guest", json={}).status_code for _ in range(12)]
        assert codes[:10] == [201] * 10      # auth limit is 10 / 60s per IP
        assert 429 in codes[10:]             # then throttled
    finally:
        ratelimit.reset()                    # monkeypatch restores the env after the test


# ── prod-secret boot guard ──────────────────────────────────────────────────────

def test_require_secrets_noop_outside_prod(monkeypatch):
    monkeypatch.delenv("MK_ENV", raising=False)
    monkeypatch.delenv("MK_JWT_SECRET", raising=False)
    require_secrets()  # no MK_ENV=prod → does not raise even with no secrets


def test_require_secrets_refuses_unset_or_insecure_in_prod(monkeypatch):
    monkeypatch.setenv("MK_ENV", "prod")
    monkeypatch.setenv("MK_WS_SECRET", "real-ws-secret")

    monkeypatch.delenv("MK_JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        require_secrets()                                  # unset JWT secret

    monkeypatch.setenv("MK_JWT_SECRET", "dev-insecure-jwt-secret-change-me")
    with pytest.raises(RuntimeError):
        require_secrets()                                  # insecure default

    monkeypatch.delenv("MK_WS_SECRET", raising=False)
    monkeypatch.setenv("MK_JWT_SECRET", "real-jwt-secret")
    with pytest.raises(RuntimeError):
        require_secrets()                                  # unset WS secret


def test_require_secrets_passes_in_prod_with_real_secrets(monkeypatch):
    monkeypatch.setenv("MK_ENV", "prod")
    monkeypatch.setenv("MK_JWT_SECRET", "a-real-jwt-secret")
    monkeypatch.setenv("MK_WS_SECRET", "a-real-ws-secret")
    require_secrets()  # does not raise
