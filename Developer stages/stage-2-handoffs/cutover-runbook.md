# Stage 2 — Cutover / Deploy Runbook

> The new stack: **WordPress = page-host only**; the game runs on a **FastAPI +
> Postgres backend** (`websocket-server/app`) behind nginx at **`/api`**. The old
> WP REST surface (`api.php`), the MySQL game schema (`db.php` / `mk_install` /
> `mk_migrate`), and the old Python WebSocket server (`main.py`) were **retired in
> S2.7**. This runbook captures the operational discipline we kept relearning.

## Services (after retirement)
| Service | Role |
|---|---|
| `db` (MySQL) | **WordPress core only** (pages/posts). *Not* game data. Orphaned `wp_mk_*` tables are harmless — left in place. |
| `wordpress` | Page-host for the shortcode pages + assets (`MK.apiBase = /api`). |
| `postgres` | The game backend's data (game state, accounts, entitlements, scores). |
| `backend` | FastAPI `app.main` — REST + WebSocket + auth + engine. |
| `nginx` | `/` → wordpress · `/api/*` → backend REST · `/api/ws/*` → backend WS. No `/ws/`. |

## 1. Secrets — fill `.env` from `.env.example`
```
cp .env.example .env   # then edit
```
Required (the backend runs with `MK_ENV=prod` and **refuses to boot** on a missing
or insecure-default secret):
- `POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD` — backend's Postgres.
- `MK_JWT_SECRET` — JWT signing. Generate: `openssl rand -hex 32`.
- `MK_WS_SECRET` — per-seat WS-token HMAC (the backend signs *and* verifies it, so a
  single value; no longer shared with WordPress). Generate: `openssl rand -hex 32`.
- `MYSQL_*` — WordPress's MySQL.

## 2. ⚠️ Rebuild the backend image on `websocket-server/` changes (QA-008)
The backend is a **built image** — a code change is NOT picked up by `up` alone.
This trap has bitten us repeatedly. After editing anything under `websocket-server/`:
```
docker compose build backend        # or: build --no-cache backend  (when in doubt)
```

## 3. Migrations — auto-run on startup
`backend-entrypoint.sh` runs `alembic upgrade head` before uvicorn, so a fresh DB
or a new migration is applied on container start. **No manual migrate step.**
(Multi-replica later: split this into a one-shot migrate job; today it's single-instance.)

## 4. Bring the stack up
```
docker compose up -d
```
Order is handled by `depends_on`. The backend waits for Postgres, migrates, then serves.

## 5. After editing `nginx/nginx.conf` — force-recreate nginx
The config is bind-mounted; a plain `up` won't reload it:
```
docker compose up -d --force-recreate nginx
```

## 6. Verify
```
docker compose ps                                  # all services Up
docker compose logs backend | tail                 # "applying Alembic migrations…" then "Uvicorn running"
curl -s http://<host>:8082/api/health              # {"status":"ok"}  (nginx /api → backend /health)
curl -s -X POST http://<host>:8082/api/auth/guest -H 'Content-Type: application/json' -d '{}'  # a JWT
```
Then a **real-browser** smoke (the WEB-002 lesson — a protocol bot ≠ a browser):
open the WordPress play page, create a table (try Basic and Harbour, ± Sharp / 10-card),
join from a second browser/incognito, start, and play a few turns through to a build.

## Rollback
This cutover is a git merge. To roll back: redeploy the previous commit
(`git revert` the merge or check out the prior tag) and `docker compose up -d --build`.
The old `wp_mk_*` MySQL tables were left intact, so the previous stack's data is still
there if a fall-back is ever needed (the new stack uses Postgres, started fresh per
plan decision #5).

## CI
- `engine-tests` — the engine package (182).
- `backend-tests` — Postgres service + Alembic + persistence/app suites.
- `php-ci` — lints the (now page-host-only) plugin PHP. The old schema-migration job
  was removed with `db.php`.
