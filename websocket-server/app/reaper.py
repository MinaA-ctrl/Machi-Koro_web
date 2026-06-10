"""Table-lifecycle reaper — a light in-process background task that clears
abandoned tables so the lobby doesn't fill with dead rooms.

Each pass (every `reaper_interval_sec`):
  * deletes waiting tables idle past `stale_waiting_min` (created, never started),
  * marks playing games idle past `abandoned_playing_min` (no game_states save) as
    'abandoned' (terminal) so they stop accumulating.

DB-driven (restart-safe). ⚠️ Runs in-process under the single-instance assumption —
at scale this becomes one designated worker / cron (on our "revisit at scale" list).
The lobby-WS host-leave path already deletes a waiting table on socket disconnect;
the reaper covers the REST-created-then-abandoned + abandoned-mid-game cases it misses.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from app.config import abandoned_playing_min, reaper_interval_sec, stale_waiting_min
from persistence import repository as repo
from persistence.database import async_session


async def reap_once() -> tuple[int, int]:
    """One reaping pass. Returns (waiting_deleted, playing_abandoned)."""
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        deleted = await repo.delete_stale_waiting(
            session, now - timedelta(minutes=stale_waiting_min())
        )
    async with async_session() as session:
        abandoned = await repo.abandon_idle_playing(
            session, now - timedelta(minutes=abandoned_playing_min())
        )
    return deleted, abandoned


async def reaper_loop() -> None:
    """Sleep-first loop (so it never fires at startup / mid-test); cancelled on
    app shutdown."""
    while True:
        await asyncio.sleep(reaper_interval_sec())
        try:
            deleted, abandoned = await reap_once()
            if deleted or abandoned:
                print(f"[reaper] deleted {deleted} stale waiting, abandoned {abandoned} idle playing")
        except Exception as e:  # never let a transient DB error kill the loop
            print(f"[reaper] error: {e}")
