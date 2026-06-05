# Stage 1 · Slice 1 (Base Game) — Close-Out Memo

> **Status (2026-06-05): REOPENED — P0 found in real browser (WEB-002).** Engine/protocol layers verified, but the actual browser client was never loaded until the owner tried it. First slice of Stage 1, scoped down per the owner's "go slower, Base game first" call. The live Harbour MVP was never disturbed (additive; Harbour stays the default).

## 🔴 WEB-002 (P0) — game unplayable in a real browser
**Symptom:** blank board (no cards), "can't connect to the table."
**Root cause:** the `/ws/{code}/game/{seat}` endpoint requires the per-seat HMAC token (Stage-0 WS-auth), but `app.js` never captured or sent it — `connectWS()` built the URL with no `?token=`, so the server closed every game socket with **4401**. No socket → no state broadcast → no cards. (`/lobby/` has no token gate, so the waiting room worked — matching the symptom.)
**Why it escaped:** (1) Stage-0 owner live-smokes (SMOKE-1, real browser) were never run; (2) B6's QA used a protocol **bot that sends the token itself**, so it structurally couldn't catch a missing-token bug in the real client; (3) PM under-weighted the "badge not eyeballed in a browser" residual — that *was* the unverified client layer.
**Fix:** `app.js` now persists `mk_token` and appends `?token=` to the game socket URL. Two token sources, because the **host and joiner are minted tokens at different moments**: the **joiner** gets theirs from the join response (`goWaiting`); the **host** gets theirs from the `/start` response (`mk_api_start_game`, seat 0) — `POST /tables` returns no token. The first fix only covered the joiner; the host needed the `/start` handler to store `res.token` too. Token TTL is 6h (covers a session). **No docker rebuild needed** — `app.js` is bind-mounted; a browser hard-refresh picks it up.
**Process lesson:** a protocol bot ≠ a browser. Any client-touching slice needs one real-browser load before sign-off. (Consider: JS syntax/lint in CI; there is none today.)
**Still needs:** owner confirmation in an actual browser before this slice can re-close.

## ✅ Delivered & verified
| Task | Result | Verified by |
|------|--------|-------------|
| B1 Config | `GameConfig` dataclass + `BASE_GAME` (Basic: 15 establishments, 4 landmarks, no City Hall) + `HARBOUR_GAME` (= live default) | Tests |
| B2 Engine seam | `create_initial_state(players_info, config=HARBOUR_GAME)` config-driven; City Hall 0-coin net gated on owning the landmark (was unconditional) | 45 characterization tests stay green |
| B3 Base tests | 12 new tests (composition, City Hall absent/present, win on 4 landmarks, config validation) | pytest |
| B4 Version wiring | `main.py` both call sites version-driven via `config_for_version`; `game_version` column + idempotent `mk_migrate()`; exposed in REST | 64 tests green (+7 mapping); PM-verified |
| B5 Web | Version picker (Basic/Harbour) + version badges in lobby/game/drawer | PM-verified vs B4 contract |
| B6 QA | Full live REST+WS playthrough, all 6 checklist items PASS | `b6-qa-report.md` |
| CI-1 / TASK-108 | `php-ci.yml` (php -l + MySQL-service migration test) + `engine-tests.yml`; gates **proven red→green** | `ci-1-gate-proof.md` (5 GitHub runs) |
| DOC-1 | Migration-discipline note | `migration-discipline.md` |

**Quality signal:** engine suite 64/64 green; CI negative-gates proven; 1 deploy bug caught pre-prod (QA-008).

## 🐞 Issues found (all resolved/recorded)
- **QA-008** — the `websocket` service is a **built image** (not bind-mounted), so `docker compose up -d` ships stale engine code; a Basic table silently built Harbour with `state.version=null`. Fixed by `docker compose build websocket`. **Now a ⚠️ callout in `deploy-checklist.md`.**

## ⏳ Residuals (non-blocking)
1. **CI is proven but not operational** — `.github/` is untracked; Actions won't run on pushes until it's committed **and pushed**. → handle in the batch commit; push to confirm first green run.
2. **Version badge not eyeballed in a GUI browser** (no interactive browser in QA env). All rendering inputs verified live. → 30-second human glance during the batch.
3. **`actions/checkout@v4`** Node-20 deprecation (forced Node 24 from 2026-06-16) — cosmetic. → bump to `v5` at commit time.

## 📦 Commit readiness (when owner chooses to land it)
Working branch still at `bdd9e5b`; 9 modified files + untracked (`game_config.py`, `tests/`, `.github/`, `Developer stages/`, etc.). The batch commit should:
- Include **`.github/`** (this is what turns CI on) and push to verify the first run.
- Add a **`.gitignore`** for `__pycache__/` / `*.pyc` (currently untracked, would otherwise be swept in).
- Bump `actions/checkout@v4` → `v5`.
- Note: `docker-compose.yml` + `.env.example` carry a `MK_WS_SECRET` addition (legit Stage-0 WS-auth infra fix) — expected in the diff.

## ➡️ Next (Stage 1, Track B — not started)
- **S1-EXTRACT** — extract engine into a standalone `machi_koro_engine/` package (headless, structured/keyed i18n-ready events).
- **S1-SHARP** — Sharp config (13 cards, renovation, landmark-loss/Demolition Co., Cleaning Co.); card list ready in `MachiKoroCardReference+SHARP.xlsx` / `sharp-card-reference.md`.
- **S1-TESTS** — grow to 100+ tests, ≥80% coverage across Basic/Harbour/Sharp.
