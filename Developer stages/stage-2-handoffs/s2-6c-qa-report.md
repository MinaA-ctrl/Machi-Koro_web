# S2.6c — Real-Browser Parity QA of the New FastAPI + Postgres Stack

**Finder:** QA · **Date:** 2026-06-10 · **Branch:** `stage-2-backend` · **Gate:** go/no-go before the S2.7 cutover
**Verdict:** ✅ **GO** — all 10 checklist items PASS, including the non-negotiables (1, 2, 5, 8). One Low finding (QA-010) filed; not a blocker.

## Environment & deploy discipline (the WEB-002 / QA-008 lesson, doubly)
- `.env` filled (POSTGRES_*, MK_JWT_SECRET, MK_WS_SECRET). `MK_ENV=prod` on the `backend` service → secrets guard + rate limiting enforced; backend booted cleanly (it refuses to boot on missing/insecure secrets, and didn't).
- `docker compose up -d postgres backend` (entrypoint auto-ran Alembic), then `up -d --force-recreate nginx`. `/api/health` → `{"status":"ok"}`.
- **Caught a stale built image first:** the `backend` image was built 13:25 but source changed to 16:05 (ratelimit.py, routers, entrypoint — directly relevant to items 4/8). **Rebuilt `backend` before any testing** (Alembic re-applied, health green). Without this the gate would have tested stale code. The backend is a built image (not bind-mounted) → **rebuild it on every deploy that touches `websocket-server/`** (carry QA-008 into the S2.7 cutover runbook).

## Method
Drove the real stack through nginx exactly as the browser does: REST `/api/*` (JWT bearer), WS `/api/ws/<code>/{game,lobby}/<seat>?token=`. Browser items via host Playwright/Chromium → `http://localhost:8082`. WS/DB-heavy items via a driver in the backend image (websockets + asyncpg + the engine). Sharp overlays + the multiplayer win used deterministic state injection into Postgres `game_states` (engine-built via `_set_interactive_phase`) before first connect, then **real DOM clicks**. Create is rate-limited 5/min → creates paced; item 8 run in isolation. Evidence screenshots in `/tmp/mkqa2/shots/`.

---

## Results — PASS/FAIL + repro per item

### 1. Full games to a win over /api/ws (exhaustive) → **PASS** ★
Six configs each bot-driven to a **natural win** (all landmarks built), zero engine errors:
| Config | market size | winner landmarks |
|---|---|---|
| Basic | 15 | 4 base |
| Harbour | 25 | city_hall + 6 |
| Basic + Sharp | 28 | 4 base |
| Harbour + Sharp | 38 | city_hall + 6 |
| Basic + 10-card (variable_supply) | 10 | 4 base |
| Harbour + Sharp + 10-card (combo) | 10 | city_hall + 6 |
- **Repro:** create a table of each config, start with 2 players, play over `/api/ws` → a player builds all landmarks → `phase=finished`, winner set. (`variable_supply` correctly caps the market at 10 types.)

### 2. Sharp interactive overlays — CLICKED IN-BROWSER → **PASS** ★ (all three)
Each rendered on the new stack, was **clicked**, engine applied the effect (read back from Postgres):
- **Cleaning Company** → picked Corn Field → both open copies closed (`renovation.corn_field=2`), **+2🪙** (3→5), phase→build.
- **Demolition Company** → picked Train Station → demolished (`built=false`, still listed ⇒ **rebuildable**), **+8🪙** (3→11), phase→build, game continues.
- **Moving Company** → Corn Field → player B → Give Card → card moved seat 0→1, **+4🪙** (3→7), phase→build.
- **Repro:** own the card + roll its number (8 / 4 / 9) with valid targets → overlay → pick → effect applies, turn proceeds.

### 3. Multiplayer — 2 contexts, create→join→play to a winner → **PASS**
- **Onboarding (real UI, 2 contexts):** A creates Basic via UI → B joins by code → A starts → both reach `/game/`; A shows "Your Turn" with the roll button, B shows "Alice"'s turn; each sees the other as an opponent. (Lobby sync, start broadcast, turn display all correct across two separate JWT identities.)
- **To a winner (2 real clients):** with both browser contexts in one game, seat 0 **clicked** the final landmark → "🎉 You Win!" end screen; **seat 1 also saw the end screen**; Postgres `winner=0`, `phase=finished`.
- **Repro:** open two browsers; A creates + B joins + A starts; play until a player completes their landmarks → both clients show the end screen.

### 4. Auth (JWT) → **PASS**
- Guest bootstrap: `POST /api/auth/guest` → 201 + access+refresh; `/api/auth/me` → 200 (kind=guest).
- Refresh rotation: `/api/auth/refresh` → 200, **distinct** new access+refresh, new access works; an access token is **rejected** as a refresh (401).
- Bad token → **401**; expired access (crafted with the real secret) → **401**.
- Game WS: good seat-0 token → opens; **bad token → 4401**; **seat-0 token replayed on seat 1 → 4401** (seat is signed).
- No impersonation: identity B `start`/`kick` on A's table → **403**.
- **Caveat (QA-010 below):** the old refresh token stays valid after rotation (not single-use).

### 5. Restart-survival (Postgres) → **PASS** ★
Mid-game `docker compose restart backend`, then reconnect with the surviving token → state reloaded from Postgres **identically** (Harbour+Sharp, game_seq 0, total coins & cards unchanged); no crash. In-memory rooms are rebuilt from the persisted row.
- **Repro:** start a game, play a few turns, restart the backend, reconnect → same game continues.

### 6. Scores + rematch → **PASS**
Registered 2-player game to finish → 2 rows in Postgres `scores` (winner: won=true/4 landmarks; loser: 1) under `game_seq=0`. `new_game` → fresh state with `game_seq=1` (distinct; QA-006 rematch-safety holds). (Guests are intentionally not scored.)
- **Repro:** finish a game with registered accounts → `scores` rows persist; rematch → new `game_seq`.

### 7. Passwords → **PASS**
Protected table: wrong password → **403**, missing password → **403**, correct password → **200** (seated); `is_protected=true` in the table detail (hash never leaked).
- **Repro:** create with a password; join wrong → 403, right → in.

### 8. Rate-limiting (security gate) → **PASS** ★
From a clean bucket: **create** 5×201 then **429** (limit 5/min); **auth** 10×201 (1 setup + 9) then **429** (limit 10/min). Per-IP fixed window, enforced because `MK_ENV=prod`.
- **Repro:** hammer `/api/tables` (6×) → 6th = 429; hammer `/api/auth/guest` (11×) → 11th = 429.

### 9. Parity vs. the old WP+MySQL stack → **PASS**
The live MVP stack **and** the new backend both import the **same `machi_koro_engine` package** (live `websocket-server/main.py:10` `from machi_koro_engine import …`; the old `game_engine.py` monolith is gone). The only differences are persistence (MySQL→Postgres) and transport/auth (WP nonce→JWT) — neither touches game logic. Empirically, a deterministic seeded game (basic + harbour) produced **byte-identical trajectory fingerprints** across both runtime images (`bd4d3045…`, `afae754b…`).
- **Repro:** run the same seeded game in the ws image and the backend image → identical fingerprint/winner/scores.

### 10. Clean — no console errors, no WP-REST/nonce → **PASS**
Across the full browser run: **0 console errors / pageerrors**; **0** `/wp-json` requests; **0** nonce/`_wpnonce` requests; all API traffic under `/api` (11 API calls observed). Static check of the served `app.js`: 0 `wp-json`/nonce occurrences; localized `apiBase="/api"`, `wsUrl=…/api/ws/`. Backend logs: no tracebacks/500s during the entire session.

---

## Bug filed

### QA-010 · Security/Auth · Low · P3 · OPEN
**Refresh tokens are not single-use — `/api/auth/refresh` rotates (issues new tokens) but never revokes the old refresh token.**
- Verified: after using a refresh token to get a new pair, **replaying the same old refresh token again returns 200** with another valid pair. There is no server-side refresh store / `jti` denylist, so a refresh token is replayable for its full 30-day TTL even after the legitimate client rotates.
- **Impact:** a stolen/leaked refresh token grants a 30-day foothold that a refresh can't invalidate. Low for the current guest-heavy, casual context (guests are low-value identities; access tokens are short-lived at 15 min), but it's a real hardening gap once registered/paid accounts arrive.
- **Repro:** `POST /api/auth/guest` → take `refresh_token` → `POST /api/auth/refresh` (200) → `POST /api/auth/refresh` with the **same** original token → **200** (expected 401 if single-use).
- **Suggested fix:** track refresh `jti` (or a per-user refresh version) and reject a refresh token once it's been rotated or on logout. Defer-able past the S2.7 cutover, but should land before registered-account features.

## Observations (no ID)
- **Rate limiter is in-memory, per-process** (documented in `ratelimit.py`): correct for a single backend instance (the cutover target); a shared store (Redis) is needed if the backend is ever scaled to multiple replicas.
- **End-screen "/6" denominator** is hardcoded, so a Basic 4-landmark win shows "4 / 6". Pre-existing and identical on the old stack (same frontend) — **not a migration regression**; cosmetic.

## Note to PM
- **GO for S2.7.** Non-negotiables (1 full wins over /api/ws, 2 overlay clicks, 5 restart-survival, 8 rate-limit) all pass; parity is structural (shared engine package) and empirically identical.
- **One must-do for the cutover runbook:** rebuild the `backend` image on deploy (it's a built image; I caught it stale at start — QA-008 again).
- **QA-010** (refresh not single-use) is the only filed bug — Low, non-blocking, recommend hardening before registered/paid accounts.
- **Did not commit** (owner batches Phase D / the cutover). Stack changes: rebuilt the `backend` image; one `restart backend` (item 5). Test data (`MK-*` tables, guest/registered users, scores) remains in Postgres — harmless.
