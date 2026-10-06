# Stage 3 — Production Deploy Runbook

> The live stack: **Caddy** (auto-HTTPS edge) → **Next.js frontend** (page-host)
> + **FastAPI backend** (`/api/*`, REST + WebSocket) + **Postgres**. The old
> WordPress page-host + MySQL were retired; see `docker-compose.legacy.yml` for
> the previous stack. This replaces the Stage 2 `cutover-runbook.md` for the
> new-design-stage3 frontend.

## Topology
| Service | Role |
|---|---|
| `caddy` | Edge proxy + automatic Let's Encrypt TLS. `/` → frontend · `/api/*` → backend (prefix stripped) · WS under `/api/ws/*` proxied transparently. |
| `frontend` | Next.js 14 standalone server (`:3000`). Talks to backend same-origin via `/api`. |
| `backend` | FastAPI `app.main` — REST + WebSocket + auth + engine. Runs `alembic upgrade head` on startup. |
| `postgres` | Game state, accounts, entitlements, scores. |

`pima.kz` (the visitka) is **not** on this server — it's free on Cloudflare Pages
(see `site/README.md`). Only `machi-koro.pima.kz` points here.

---

## 1. Provision the VPS (Hetzner CAX11, ARM, ~€3.79/mo)
1. console.hetzner.cloud → new project → new server.
2. **CAX11** (ARM 2 vCPU / 4 GB), image **Ubuntu 24.04**, add your SSH key.
3. SSH in, install Docker + compose plugin:
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```
4. Firewall: allow 22, 80, 443 (Hetzner Cloud Firewall or `ufw`).

## 2. DNS (Cloudflare)
- Move `pima.kz` nameservers to Cloudflare (registrar side; .kz supports it).
- Add **A** record: `machi-koro` → `<VPS IPv4>`, **Proxy status = DNS only**
  (grey cloud). This lets Caddy complete the ACME challenge and run WebSockets
  without a second TLS hop. (`pima.kz` / `www` can stay proxied → Pages.)

## 3. Secrets — fill `.env`
```bash
git clone <repo>            # Amina's MinaA-ctrl/Machi-Koro_web
cd Machi-Koro_web
git checkout new-design-stage3
cp .env.example .env
```
Edit `.env` — the backend runs `MK_ENV=prod` and **refuses to boot** on a missing
or insecure-default secret:
- `SITE_DOMAIN=machi-koro.pima.kz`
- `POSTGRES_PASSWORD=<pick one>`
- `MK_JWT_SECRET=$(openssl rand -hex 32)`
- `MK_WS_SECRET=$(openssl rand -hex 32)`

(The `MYSQL_*` vars are legacy — only the rollback compose uses them.)

## 4. Bring the stack up
```bash
docker compose up -d --build
```
`backend` and `frontend` are **built images** — `up` alone won't pick up code
changes. After editing `websocket-server/` or `frontend/`:
```bash
docker compose build backend frontend && docker compose up -d
```
The backend waits for Postgres, runs Alembic, then serves. Caddy fetches a
certificate for `SITE_DOMAIN` on first request (allow a few seconds).

## 5. Verify
```bash
docker compose ps                                    # all Up
docker compose logs backend | tail                   # Alembic … then Uvicorn running
docker compose logs caddy | tail                     # certificate obtained
curl -s https://machi-koro.pima.kz/api/health        # {"status":"ok"}
curl -s -X POST https://machi-koro.pima.kz/api/auth/guest \
     -H 'Content-Type: application/json' -d '{}'      # a JWT
```
Then a **real-browser** smoke (the WEB-002 lesson): open the site in two browsers,
create a table (try Basic and Harbour, ± Sharp / 10-card), join from the second,
start, and play a few turns through to a build. WebSocket stays live across turns.

**Restart-survival:** `docker compose restart backend` mid-game → state reloads
from Postgres and the game continues.

## Updating the server (git)
The server folder `~/Machi-Koro_web` is a git checkout of the deploy branch. **Keep
the folder name**: compose names the project (and the `pg_data` volume) after it,
so a renamed/moved folder would start against an empty database.

```bash
cd ~/Machi-Koro_web
git fetch origin
git status                      # must be clean before updating
git log --oneline HEAD..origin/new-design-stage3   # what's about to change
git pull
docker compose build backend frontend && docker compose up -d
```
Then run the checks in **5. Verify**. To roll back one release:
`git checkout <previous-commit>` and rebuild the same way.

Not in git (stay on the server only): `.env` (secrets) and
`docker-compose.override.yml` (per-host port overrides — on this host Caddy's
HTTPS listens on `127.0.0.1:8443` behind a port-443 multiplexer, which is why the
`Caddyfile` enables `proxy_protocol`). Compose loads the override automatically.

## Local HTTP smoke (no domain/cert)
Set `SITE_DOMAIN=:80` in `.env`, `docker compose up -d --build`, then browse
`http://<host>/` and `curl http://<host>/api/health`. (Caddy serves plain HTTP;
no Let's Encrypt.)

## Rollback
The new-design-stage3 deploy is a branch checkout. To fall back to the WordPress
stack: `docker compose down`, then `docker compose -f docker-compose.legacy.yml up -d`
(fill the `MYSQL_*` vars first). Postgres game data is on the `pg_data` volume and
is untouched by the legacy stack.

## CI
- `engine-tests` — engine package (200 green locally).
- `backend-tests` — Postgres service + Alembic + persistence/app suites.
- `php-ci` — lints the (now unused) legacy plugin PHP.
- *Not yet covered:* a frontend build/lint job and an end-to-end smoke. Worth
  adding a `frontend` workflow (`bun install && bun run build && bun run typecheck`).
