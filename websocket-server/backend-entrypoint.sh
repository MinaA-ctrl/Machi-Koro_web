#!/bin/sh
# Apply Alembic migrations, then serve the backend. Migrate-on-startup keeps a
# single-instance deploy simple; for multi-replica, split this into a one-shot
# migrate job and have the app containers wait on it.
set -e

echo "[backend] applying Alembic migrations…"
( cd /app/persistence && alembic upgrade head )

echo "[backend] starting uvicorn app.main:app…"
# --ws-max-size: client frames are tiny; refuse anything over 64 KiB at the socket.
exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --ws-max-size 65536
