# Stage 0 — Stabilization · Close-Out Memo

> PM close-out for Sprint 1 (Stage 0 of the PRD roadmap). Pairs with `sprint-1-review-retro.md`.
> **Decision:** Stage 0 is **delivered and conditionally closed** — the only thing between us and a full stamp is 3 owner-run smokes on the **live** stack (see below). Those smokes gate the "fully closed" stamp; they do **not** block Stage 0.5 or Stage 1 from starting.

## ✅ Delivered (all 6 tasks, 29/29 SP)
| Task | Result | Verified by |
|------|--------|-------------|
| TASK-001 Persistence | Per-action write-then-broadcast; UNIQUE `table_id`; survives restart | QA + 45-test harness |
| TASK-002 WS auth | HMAC per-seat token; no impersonation | QA |
| TASK-003 REST lockdown | Host/seat authz, input validation, IP-fallback rate-limit | QA |
| TASK-004 Scores | Per-game `game_seq`; atomic upsert; rematch-safe | QA + harness |
| TASK-005 Engine harness | 45 tests green in CI (4 regression guards) | CI |
| TASK-006 Passwords | Create/join/enforce + 🔒 UI; no `password_hash` leak | QA + Web |

Quality signal: **11 issues caught pre-prod, 0 escaped.** The QA + deploy gate worked as designed.

## ⏳ Exit condition remaining — OWNER ACTION (needs the live stack)
These are manual functional smokes that can only run against the live/staging Docker stack — I can't execute them from here. Run all three, tick them, and Stage 0 is fully closed:
- [ ] **① Restart-survival** — start a game, force-restart the WS server mid-game, confirm no in-progress game is lost (TASK-001).
- [ ] **② Password flow + no-leak** — create a protected table, join with right/wrong password, confirm enforcement and that no `password_hash` is exposed in any API response (TASK-006).
- [ ] **③ Scores + rematch** — finish a game, confirm registered results land in `wp_mk_scores` exactly once; play a rematch at the same table and confirm `game_seq` keeps them distinct (TASK-004).

> To run: `docker compose up -d`, then walk the three flows on the play page. ③ is also harness-verified, so it's the lowest-risk of the three.

## 📦 Carry-forward into Stage 1 (from the retro action items)
| # | Item | Why it carries | Owner |
|---|------|----------------|-------|
| 1 | **Add MySQL + PHP-lint to CI** | *Highest leverage.* CI today runs only `pytest` (no DB, no `php -l`) — migrations and PHP syntax went unverified until a manual sweep (root cause of the DEPLOY-001 near-miss). | Backend/DevOps |
| 2 | **Enforce Definition of Done** | TASK-001/004 were each called "done" then failed QA. "Code written" ≠ done; require QA-verified **and** staging-checked. | PM (process) |
| 3 | **Document migration discipline** | `dbDelta` silently fails to add UNIQUE indexes over existing dup rows; use explicit migrations + verify with `SHOW INDEX`. | Backend |
| 4 | **Connection pooling** | Replace per-action `aiomysql.connect()` — fold into the FastAPI/SQLAlchemy work, not a Stage-0 patch. | Stage 1/2 Backend |
| 5 | **Bug-ID convention** | ✅ already adopted (area prefixes, finder-owns-ID). Keep enforcing via briefs. | All |

## 🚦 Gate decision (what can start now)
- **Stage 0.5 (frontend polish)** — ✅ cleared to start. Independent of the 3 smokes; Web-developer owned; no engine coupling.
- **Stage 1 (engine extraction)** — ✅ cleared to start. The 45-test harness (TASK-005) is the safety net it was built to be. ⚠️ Still needs the **Sharp card-list spike** resolved before Stage 1.2 (flagged in the PRD risk table as a blocker, not an assumption).
- The 3 smokes gate the **"Stage 0 fully closed"** stamp only — not downstream start.
