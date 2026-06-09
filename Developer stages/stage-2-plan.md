# Stage 2 Plan — Backend: FastAPI + PostgreSQL

> **Status (2026-06-09): PLANNED.** Per the PRD roadmap (initial plan). Collapse the split WordPress-PHP + Python-WS backend into **one FastAPI service on PostgreSQL**, importing the headless engine, with JWT auth and a monetization-ready entitlements seam.
> **Builds on:** Stage 1 complete (Basic/Harbour/Sharp/Variable-Supply engine, 182 tests, committed `aa73bac` on `Stage-1_add_base`).
> **Note:** this is the PRD's Stage 2, done the *light* way — evolve in place, **not** the dropped "diversification" monorepo restructure.

## Goal
A single **FastAPI + PostgreSQL** backend that owns all REST + WebSocket logic, imports `machi_koro_engine`, authenticates with **JWT** (guest + registered), persists via **Alembic migrations**, and carries a **free-by-default entitlements seam** so monetization slots in later. The live game plays identically throughout.

## Strategy
- **Evolve in place.** The current `websocket-server/main.py` is already FastAPI — grow it into the full backend (add REST, Postgres, JWT, entitlements). Reimplement the WordPress PHP backend (`api.php`/`db.php`) in Python; **retire** it. WordPress is **demoted to a page-host** for the existing JS frontend until React replaces it (Stage 3).
- **Keep the MVP live.** Build alongside; cut over at parity. The shared engine means rules never fork.
- **Light, not a restructure.** No `engine/ backend/ frontend/ db/` monorepo reshuffle (that was the dropped diversification). Engine becomes an importable package; the FastAPI service stays where it is; WordPress plugin stays as the page-host.

## Key decisions (recommended defaults — confirm or override)
| # | Decision | Recommended default |
|---|----------|---------------------|
| 1 | Migration approach | **Evolve the existing FastAPI service in place** (not greenfield, not monorepo restructure) |
| 2 | WordPress's role | **Demote to page-host**; retire its PHP backend (`api.php`/`db.php`); full removal at Stage 3 (React) |
| 3 | Branch | **`stage-2-backend`** off `Stage-1_add_base` (merge Stage-1 → `main` first as the stable baseline) |
| 4 | Auth | **JWT** (access + refresh); guest tokens too; replaces WP nonce/guest-id + the HMAC WS token (keep per-seat signing) |
| 5 | Data | **Start fresh** (in-progress games disposable); migrate users/scores only if we decide they matter — defer that script |
| 6 | Entitlements scope | **Seam only, free by default** (`can_host` check + account + wallet stub); Stripe/RevenueCat/shop deferred to Stages 7/8 |

## Phases

### S2.1 — Extract the engine  · Backend  *(keystone; deferred from Stage 1)*
- [ ] Move `card_defs.py`, `game_config.py`, `game_engine.py` (+ tests) into an importable `machi_koro_engine` package; repoint the current WS server's imports.
- **AC:** engine imports with no transport/DB deps; **182 tests green from the new location**; live MVP still plays.
- **DoD:** CI green; short package README; the FastAPI service imports the package.

### S2.2 — Postgres + persistence  · Backend
- [ ] Add a `postgres` service (compose); SQLAlchemy models + **Alembic** migrations for: tables, players, game_states, scores — **plus** users / entitlements / wallet (S2.5).
- [ ] Port per-action state writes + scores from MySQL/PHP to SQLAlchemy/Postgres; preserve restart-safety.
- **AC:** a full game persists per action to Postgres and survives a backend restart; migrations run clean in CI (fresh + upgrade).
- **DoD:** CI boots Postgres + applies migrations; restart-survival verified.

### S2.3 — REST API on FastAPI  · Backend
- [ ] Reimplement the WP REST surface in FastAPI: create / join / start / list / kick / rename, passwords — server-authoritative, through the engine.
- **AC:** every current REST flow works on FastAPI with **behavioral parity** to WP+WS.
- **DoD:** `backend-tests` CI job (pytest + Postgres service); parity checklist passed.

### S2.4 — JWT auth + account model  · Backend
- [ ] JWT issuance/verification (access + refresh); guest tokens; per-seat game-WS auth re-expressed on JWT (keep the per-seat signing concept).
- [ ] Account model: kind (guest/registered), display_name, **language**, avatar.
- **AC:** register / login / guest all issue valid JWTs; the game WS authenticates per seat; no impersonation (Stage-0 property preserved).
- **DoD:** auth tests; **security review** of the JWT + WS-token path.

### S2.5 — Entitlements seam  · Backend
- [ ] `users` / `entitlements` / `wallet` tables; an `can_host(version, sharp, variable_supply)` check at table creation that **returns allowed for everything** today.
- [ ] Structure the **host-pays / join-free** model (one-free-host consumable, registered-only) — wired but all-free; wallet (Koro Coins) stub.
- **AC:** table creation passes through the entitlements check (all-allow now); joining is never gated; flipping a default later gates hosting with no re-architecture.
- **DoD:** entitlement-check tests (all-allow + a forced-deny unit test proving the gate works).

### S2.6 — Frontend cutover (interim)  · Web
- [ ] Point the existing JS client at FastAPI (JWT auth flow; REST + WS to the new backend). WordPress now just serves the pages.
- **AC:** the current UI plays Basic/Harbour/Sharp/VS against the new backend, no regressions — **verified in a real browser** (the WEB-002 lesson).
- **DoD:** real-browser QA report.
- **→ Stage 3:** the React + TS rebuild (with i18n EN/RU) replaces the WP-hosted JS. **Prereq: create a `designer` agent.**

### S2.7 — Cutover & retire PHP backend  · Backend / owner
- [ ] Switch live deploy to FastAPI + Postgres; freeze/remove `api.php` + `db.php`.
- [ ] Decide data: fresh start vs. migrate users/scores (per decision #5).
- **DoD:** FastAPI + Postgres is the live backend; WP serves only pages.

## Sequencing
S2.1 (extract) → S2.2 (Postgres) → S2.3 (REST) ∥ S2.4 (JWT) → S2.5 (entitlements) → S2.6 (frontend cutover) → S2.7 (retire PHP). QA parity passes throughout; **real-browser** check before cutover.

## Risks
| Risk | P | Impact | Mitigation |
|------|---|--------|------------|
| Migration drags on (solo dev) | High | High | Evolve-in-place + small steps; MVP stays live; ship S2.1–S2.5 before frontend cutover |
| Rules re-bugged in the rewrite | Med | High | **Shared extracted engine** — backend imports it, never reimplements; 182 tests guard it |
| Auth rewrite (→ JWT) opens a hole | Med | High | Keep per-seat signing; **security review** of JWT + WS path before cutover |
| Parity gaps vs. the WP backend | Med | Med | Parity checklist; QA compares new vs. old behavior (same engine helps) |
| Data migration surprises | Low | Med | Default to fresh start; script only what we keep, tested in CI |
| Two stacks in parallel during cutover | Med | Med | Cut over only at proven parity; document both in compose |

## "Stage 2 done" =
A single **FastAPI + Postgres** backend serving Basic/Harbour/Sharp/VS at parity, **JWT** auth (guest + registered), the **engine as a package**, the **entitlements seam** (free), **Alembic** migrations, and the existing frontend playing against it — WordPress reduced to a page-host. PHP backend retired. Next: **Stage 3 (React + i18n)**.

**Estimate:** 2–3 sprints (PRD).
