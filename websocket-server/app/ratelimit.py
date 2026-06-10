"""Lightweight per-IP rate limiting (S2.6a) — ports the Stage-0 / WP IP-fallback
concept (mk_client_ip + a fixed-window counter) without a new dependency.

Enabled in prod (MK_ENV=prod) or when MK_RATE_LIMIT is truthy; **off by default**,
so backend-tests aren't throttled (the test-mode bypass). One test flips it on to
prove it works. In-memory + per-process — fine for a single instance; a shared
store (Redis) is the multi-replica upgrade.
"""
import os
import time

from fastapi import HTTPException, Request

# (name, ip) -> [count, window_start]
_buckets: dict[tuple[str, str], list] = {}


def _enabled() -> bool:
    return os.getenv("MK_RATE_LIMIT", "").lower() in ("1", "true", "on") \
        or os.getenv("MK_ENV", "").lower() == "prod"


def _client_ip(request: Request) -> str:
    """Best-effort client IP (mirrors WP mk_client_ip): X-Real-IP (nginx sets it
    from $remote_addr), else the last hop of X-Forwarded-For, else the socket peer."""
    ip = (request.headers.get("x-real-ip") or "").strip()
    if not ip:
        xff = request.headers.get("x-forwarded-for", "")
        ip = xff.split(",")[-1].strip() if xff else ""
    if not ip:
        ip = request.client.host if request.client else "0.0.0.0"
    return ip


def reset() -> None:
    """Clear all buckets (used by tests)."""
    _buckets.clear()


def limit(name: str, max_calls: int, window: int):
    """A FastAPI dependency enforcing `max_calls` per `window` seconds per client IP
    for the bucket `name`. 429 when exceeded. No-op when disabled."""
    def dependency(request: Request) -> None:
        if not _enabled():
            return
        key = (name, _client_ip(request))
        now = time.time()
        bucket = _buckets.get(key)
        if bucket is None or now - bucket[1] >= window:
            _buckets[key] = [1, now]
            return
        if bucket[0] >= max_calls:
            raise HTTPException(status_code=429, detail="Too many requests — please slow down")
        bucket[0] += 1
    return dependency


# Shared limiters (mirror the WP windows: create 5/min; auth a bit looser).
auth_limit = limit("auth", 10, 60)
create_limit = limit("create", 5, 60)
