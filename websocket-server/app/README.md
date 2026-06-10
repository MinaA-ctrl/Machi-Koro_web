# app — Stage-2 FastAPI backend (S2.3: REST surface)

The new backend's HTTP API: a FastAPI reimplementation of the WordPress `api.php`
tables surface, on the S2.2 Postgres repository + the `machi_koro_engine` package.

**This is the live game backend (since S2.7).** WordPress is page-host only; the old
WP REST surface, the MySQL game schema, and the old Python WebSocket server
(`main.py`) were retired. nginx routes `/api/*` (REST) and `/api/ws/*` (WebSocket)
here. See `Developer stages/stage-2-handoffs/cutover-runbook.md` for deploy steps.

## Running it (S2.6a) — compose service + nginx routing
`docker compose up` brings up `postgres` + **`backend`** (`app.main:app`,
`Dockerfile.backend`) next to the live `wordpress` + `websocket` + `nginx`. The
backend **applies Alembic migrations on startup** (`backend-entrypoint.sh`) then
serves uvicorn on `:8001`. It reads Postgres via `DB_*` and requires
`MK_JWT_SECRET` + `MK_WS_SECRET` (it sets `MK_ENV=prod`, so it **refuses to boot**
on missing/insecure secrets).

### nginx path scheme — the **S2.6b contract** (where the JS points)
The new backend is reachable through nginx under `/api`, run *alongside* the live
routes (which are untouched), so both stacks serve in parallel:

| Path (browser) | → upstream | Service |
|---|---|---|
| `/api/<rest>` | `backend:8001/<rest>` | new REST (`/api/auth/*`, `/api/tables`, …) |
| `/api/ws/<code>/{game,lobby}/<seat>` | `backend:8001/ws/...` | new game/lobby WebSocket |
| `/ws/...` | `websocket:8001` | **live** WS (main.py/MySQL) — unchanged |
| `/` | `wordpress:80` | WordPress page-host — unchanged |

So S2.6b points the JS client at **`/api/...`** for REST and **`/api/ws/...`** for
sockets. nginx strips the `/api` prefix (trailing-slash `proxy_pass`) and forwards
`X-Real-IP` / `X-Forwarded-For` (the rate limiter keys on it). Live traffic flips
to `/api` only at **S2.7**.

## Security gates (S2.6a)
- **Real secrets enforced:** `MK_ENV=prod` → `require_secrets()` (lifespan) aborts
  boot if `MK_JWT_SECRET` is unset/insecure or `MK_WS_SECRET` is unset. Dev/test
  (no `MK_ENV`) skips the guard.
- **Rate limiting** (`app/ratelimit.py`, per-IP fixed window, ports the WP
  `mk_client_ip` fallback): `/auth/register|login|guest` 10/60s, table create 5/60s
  → 429 when exceeded. **On** in prod (or `MK_RATE_LIMIT=on`); **off by default** so
  tests aren't throttled (one test flips it on to prove it works).

## Layout
```
app/
├── main.py            # FastAPI() instance + /health; includes the tables + ws routers
├── routers/tables.py  # the 7 REST endpoints (S2.3a)
├── ws.py              # game + lobby WebSockets on Postgres + the engine (S2.3b)
├── schemas.py         # Pydantic v2 request/response models
├── auth.py            # passwords (argon2), per-seat HMAC token (mint+verify), identity dep
├── deps.py            # get_session, valid_code, clean_name
├── pytest.ini         # app/API suite config (run from this dir)
└── tests/             # TestClient REST + WebSocket tests (need a live, migrated Postgres)
```

## WebSockets (S2.3b)
A faithful port of `main.py`'s WS loop onto the Postgres repo + `machi_koro_engine`:
- **`/ws/{code}/game/{seat}`** — verifies the per-seat token (4401 on bad/missing/
  wrong-seat); loads/creates state via the repo (`load_state`/`save_state`); runs
  actions through `handle_action` (all interactive flows: harbor/reroll/TV/business-
  center/tuna + Sharp cleaning/demolition/moving/tech-startup-invest); **write-then-
  broadcast**; reactions; reconnect; `new_game` rematch (reads the table's flags via
  the repo → `config_for(version, sharp, variable_supply)`, `game_seq+1`).
- **`/ws/{code}/lobby/{seat}`** — `player_joined/left/kicked/renamed/game_started`
  broadcasts (no token gate, as today); deletes/removes waiting-table rows on leave.
- A per-code `asyncio.Lock` serializes state read/mutate/persist; `save_scores` runs
  on finish (rematch-safe via `UNIQUE(table_id, game_seq, user_id)`).

Stage-0 properties preserved: restart-survival (TASK-001 — state reloads from
Postgres on reconnect), per-seat auth (TASK-002), write-then-broadcast (QA-001),
rematch-safe scores (TASK-004/QA-006).

## Endpoints (parity with `api.php`)
| Method | Path | Notes |
|---|---|---|
| POST | `/tables` | create → `{code, seat:0, token}`; host = seat 0 |
| POST | `/tables/{code}/join` | join → `{seat, token}`; password enforced |
| POST | `/tables/{code}/start` | host-only, ≥2 players → `{started, players, token}` |
| GET | `/tables` | list public+waiting (`?search=`) → flags, `player_count`, `is_protected` |
| GET | `/tables/{code}` | detail: players + flags + `is_protected` (no `password_hash`/`creator_id`) |
| POST | `/tables/{code}/kick` | host-only, waiting-only, by `seat` |
| POST | `/tables/{code}/rename` | host or seat-owner; unique display name |

## Auth (S2.4 — JWT + accounts)
`/auth` (`routers/auth.py`): `POST /register` · `POST /login` · `POST /guest` ·
`POST /refresh` · `GET /me`. All issue a `{access_token, refresh_token,
token_type:"bearer"}` pair.
- **Accounts:** the `users` table (kind `guest` | `registered`). Registered carry a
  unique email + argon2 `password_hash`; guests are persisted (kind `guest`) so the
  no-friction flow has a stable identity. `/auth/guest` keeps guests first-class.
- **JWT (HS256, PyJWT):** the subject is the identity string `guest:<id>` /
  `user:<id>` (id = `users.id`) — the same value S2.3 authorized on. Access TTL
  **15 min**, refresh **30 days**; `/auth/refresh` rotates both. `type` claim
  enforced (an access token can't refresh). Signature + expiry verified by PyJWT.
- **Identity dep:** `current_identity` is now a **JWT bearer** dependency (replaces
  the X-MK-Guest header). REST host/seat authz reads the verified subject;
  `tables.creator_id` / `players.identity` hold it. A registered subject also sets
  `players.user_id` (→ scores); guests don't (NULL).
- **Per-seat game-WS token:** unchanged HMAC scheme (`mint_ws_token` /
  `verify_ws_token`), now **carrying the verified JWT subject**. It's minted only by
  an authenticated REST call (create/join/start) and is the socket's trust anchor —
  the WS does not decode a JWT on the hot path; it verifies the per-seat HMAC, which
  is bound to (code, seat, identity) and not replayable.
- **Passwords:** argon2; hashed on register, verified on login/join, never returned.

## Security review (S2.4 — JWT + WS-token path)
- **Signature/expiry:** JWTs are HS256, verified by PyJWT (`jwt.decode` checks sig +
  `exp`); tampered/expired/missing → 401 (tested). The WS token is HMAC-SHA256 with
  its own `exp`, `compare_digest` comparison; tampered/expired/wrong-seat → 4401.
- **No impersonation:** `seat` is inside the signed WS payload, so a token for one
  seat can't be replayed on another (tested 4401). The WS token is mintable only via
  an authenticated REST endpoint.
- **No secret leakage:** secrets come from env (`MK_JWT_SECRET`, `MK_WS_SECRET`),
  never serialized; password hashes are never in any response (tested).
- **No user enumeration:** login returns the same 401 for unknown email vs wrong
  password.
- **Refresh:** separate long-lived token, `type:"refresh"` enforced, rotated on use.
  Short access TTL (15 min) limits a leaked access token's window.
- **Known gaps (acceptable for parallel/non-live; revisit before cutover):** no
  refresh-token revocation/denylist (rotation only — a stolen refresh stays valid
  until expiry); no rate limiting on `/auth/*` (was a WP transient stand-in; add
  slowapi at cutover); dev secret defaults are insecure and **must** be set in prod.

## Entitlements seam (S2.5 — ALL FREE until Stage 8)
The monetization-ready gate. **Nothing is gated, nothing is charged today** — it
only reads, with permissive defaults; the shape lets a later default-flip enforce
the host-pays / join-free model with no re-architecture.
- **Tables (migration 0004):** `entitlements` (per-user host-rights `host_harbour`/
  `host_sharp`, one-free-host `free_host_*_used`, subscription `harbour_pass`
  none|active + expiry, `ad_free`) and `wallets` + `wallet_ledger` (Koro Coins). All
  defaults permissive/free.
- **`can_host(session, identity, version, sharp, variable_supply) -> (allowed, reason)`**
  (`app/entitlements.py`), wired into **`POST /tables`** only:
  - **Variable Supply** — a free mode, **never gated**.
  - **Basic** base — always free to host.
  - **Harbour** base / **Sharp** add-on — each needs a host-right (explicit
    entitlement, active `harbour_pass`, or an unused one-free-host). Defaults grant
    all of these today, so create is all-allow; a missing entitlements row = all-free.
  - **Join is never gated.** Free-host *consumption* is **Stage 8** — only the shape
    here.
- **Wallet (`app/wallet.py`):** `get_balance` (real read, 0 default) + `earn`/`spend`
  **stubs** (adjust balance + ledger) — present for the shape, wired to no flow.
- A forced-deny test (set an entitlement denied → create returns 403) proves the
  gate is live, so flipping a default later actually gates.

## Config (env)
Postgres via `DB_*` (or `DATABASE_URL`) — see `persistence/`. **`MK_JWT_SECRET`**
signs JWTs; **`MK_WS_SECRET`** signs the per-seat WS token (shared with the WS
service). Dev defaults are insecure — set both in prod.

## Tests
Need a live Postgres with migrations applied (CI's `backend-tests` job runs
`alembic upgrade head`, then the persistence + app suites):
```
cd websocket-server/app && python -m pytest
```
Sync FastAPI `TestClient` drives the async app; each test starts from a clean DB.
Covers auth (register/login/refresh/me/guest, JWT verify), create/join/start/list/
detail/kick/rename + password enforcement, no-leak, host/seat authz off the JWT
subject, WS gameplay, restart-survival, and per-seat WS auth (incl. impersonation).
