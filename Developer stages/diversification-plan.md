# Diversification Plan — 3-Tier Split (= Stage 2: Backend)

> **Status (2026-06-08): PLANNED.** Branch-isolated migration of the current WordPress+MySQL+Python-WS hybrid into clean tiers: **React (frontend) / FastAPI (backend) / Postgres (database)**, with one backend instead of two. Maps to PRD **Stage 2**; the React frontend completes in **Stage 3**.
> **Keystone:** the engine is already complete and proven (160 tests, 88% coverage). Extracting it once makes the whole migration safe — the rules never get rewritten or re-bugged.

## Goal
Collapse today's tangled architecture —
- **Frontend:** WordPress PHP shortcodes + vanilla JS
- **Backend:** *split* between the WordPress plugin (REST/auth/lobby/DB in PHP) **and** the Python WebSocket server (game)
- **Database:** MySQL via WordPress

— into three clean tiers sharing one engine: `engine/` ← `backend/` (FastAPI) ← `frontend/` (React), on **Postgres**.

## Strategy: strangler-fig, not big-bang
Build the new stack **alongside** the live MVP, behind the **same shared engine**, and cut over piece by piece. The live game keeps working the entire time. This is the PRD's explicit mitigation for the "migration drags on / breaks the product" risk.

## Git / branch workflow
1. **Promote the proven work to a stable baseline:** merge `Stage-1_add_base` → `main` (the known-good "game works" anchor; current `main` is stale).
2. **Branch `diversification` off `main`.** All D1–D4 work lives there.
3. **Each step = a small, reviewable commit**, CI per push.
4. **Keep `main` deployable**; merge `main` → `diversification` periodically so the branch doesn't rot and the live MVP can still take a hotfix.
5. **Cut over only when the new stack is genuinely at parity** — then merge `diversification` → `main` and retire `legacy-wp/`.

## Target repository layout
```
machi-koro/
├── engine/                  # D1 — shared, framework-agnostic core
│   ├── machi_koro_engine/   #   card_defs.py, game_config.py, game_engine.py
│   ├── tests/               #   the 160 tests, moved as-is
│   └── pyproject.toml       #   installable local package
├── backend/                 # D2 — FastAPI: REST + WebSocket + JWT (one backend)
│   ├── app/ (main.py, routes/, ws/, db/, auth/)
│   ├── requirements.txt
│   └── Dockerfile
├── db/                      # D3 — Postgres: Alembic migrations
├── frontend/                # D4 / Stage 3 — React + TS (replaces the WP UI)
├── legacy-wp/               # current MVP — frozen, deleted after cutover
│   └── machi-koro/ (php + assets)
├── infra/                   # docker-compose.yml, nginx/
├── docs/                    # PRD + card reference (.xlsx/.docx)
├── Developer stages/        # plans, handoffs (unchanged convention)
├── .github/workflows/       # engine-tests, php-ci, + backend-tests
└── .gitignore .env.example README.md
```

---

## Phases

### D0 — Baseline & branch  · Owner: PM/owner
- [ ] Merge `Stage-1_add_base` → `main`.
- [ ] Create `diversification` off `main`.
- **DoD:** `main` is the shippable Stage-1 state; `diversification` exists and is even with `main`.

### D1 — Extract the engine  · Owner: Backend  *(the keystone)*
- [ ] Move `card_defs.py`, `game_config.py`, `game_engine.py` → `engine/machi_koro_engine/`; add `__init__.py` + `pyproject.toml`.
- [ ] Move `websocket-server/tests/` → `engine/tests/`.
- [ ] Repoint the **legacy WS server's imports** to the installed package (proves the live MVP runs on the extracted engine).
- [ ] Move `wp-plugin/` → `legacy-wp/`; `docker-compose.yml`/`nginx/` → `infra/`; update mount paths.
- **AC:** engine imports with **no transport/DB dependencies**; **160 tests green from the new location**; the legacy stack still plays a full game locally.
- **DoD:** CI green; `infra/docker-compose.yml up` runs the unchanged MVP against the extracted engine; short `engine/README.md`.
- **Note (deferred):** the engine still emits English log strings. The *structured/keyed-event* (i18n-ready) refactor is a separate follow-on, best done when Stage 3's i18n frontend needs it — **not** in D1 (keep D1 behavior-identical).

### D2 — FastAPI backend  · Owner: Backend
Build `backend/` as the **single** backend, importing `engine/`, **targeting Postgres natively** (no MySQL).
- [ ] FastAPI app: REST (create/join/start/kick/rename/list, passwords) — **reimplemented from `api.php`**.
- [ ] WebSocket (game + lobby) — evolved from today's `main.py` (already FastAPI).
- [ ] **JWT auth** replacing WP nonce/guest + the per-seat HMAC WS token (keep the per-seat signing concept).
- [ ] SQLAlchemy models + session; server-authoritative actions through the engine.
- **AC:** every current REST/WS flow works against the FastAPI backend with **behavioral parity** to the WP+WS stack (same engine = same rules); JWT issues/verifies per-seat.
- **DoD:** `backend-tests` CI job (pytest, with a Postgres service); parity checklist passed; no engine logic duplicated in the backend.

### D3 — Postgres + data  · Owner: Backend
- [ ] Postgres schema as **Alembic migrations** (replaces `db.php`/`dbDelta`).
- [ ] `infra/docker-compose.yml`: add a `postgres` service; wire `backend` to it.
- [ ] **Data-migration decision** (see below): migrate historical users/scores, or start fresh (in-progress games are disposable).
- **AC:** a full game persists per-action to Postgres and survives a backend restart; migrations run clean in CI (fresh + upgrade).
- **DoD:** CI boots Postgres + applies migrations; restart-survival verified; data-migration script (if in scope) tested.

### D4 — Frontend cutover (interim)  · Owner: Web
- [ ] Point the **existing vanilla-JS client** at the FastAPI backend (WP stays page-host short-term per the decision below).
- [ ] Validate parity in a **real browser** (the WEB-002 lesson).
- **AC:** the current UI plays Basic/Harbour/Sharp against the new backend with no regressions.
- **DoD:** real-browser QA report; the FastAPI stack is the one serving real play.
- **→ Stage 3** (separate plan): the full **React + TS** rebuild with i18n (EN/RU) replaces `legacy-wp/`. **Prerequisite: create a `designer` agent.**

### D5 — Cutover & retire  · Owner: PM/owner
- [ ] Switch live deploy to FastAPI+Postgres; freeze `legacy-wp/` PHP backend.
- [ ] Merge `diversification` → `main`.
- [ ] Delete `legacy-wp/` once React (Stage 3) replaces the UI.

---

## Decisions (recommended defaults — confirm or override)
| # | Decision | Recommended default |
|---|----------|---------------------|
| 1 | Migration style | **Incremental / strangler** (decided) |
| 2 | Scope of this plan | **Backend + DB now (D1–D3); React frontend is a separate Stage 3** — don't do a backend migration *and* a full React rewrite at once |
| 3 | WordPress's fate | **Stays as page-host short-term**, calling FastAPI; retired when React lands. Drives auth change WP nonce/guest → **JWT** |
| 4 | Historical data | **Start fresh** for in-progress games (disposable); migrate users/scores only if we decide they matter — defer the script until then |
| 5 | New backend DB | **Postgres from the start** in `backend/` (don't wire the new backend to MySQL) |

## Risks
| Risk | P | Impact | Mitigation |
|------|---|--------|------------|
| Migration drags on (solo dev, big surface) | High | High | Strangler + small commits; MVP stays live; ship D1–D3 before any React |
| Rules re-bugged during rewrite | Med | High | **Shared extracted engine** — backend imports it, never reimplements; 160 tests guard it |
| Auth rewrite (nonce/guest → JWT) introduces a hole | Med | High | Port the per-seat signing concept; security-review the JWT/WS token path |
| Long-lived branch drifts from main | Med | Med | Merge `main` → `diversification` regularly; keep each D-step independently reviewable |
| Two stacks running in parallel = deploy confusion | Med | Med | `infra/` documents both; cut over only at proven parity (D5) |
| Data migration surprises | Low | Med | Default to fresh start; script only what we keep, tested in CI |

## "Diversification done" =
`main` runs **FastAPI + Postgres** serving Basic/Harbour/Sharp at full parity, the **engine is a shared package** with 160+ tests green in CI, `legacy-wp/` is frozen (PHP backend retired), and the only remaining tier is the **React frontend (Stage 3)**.
