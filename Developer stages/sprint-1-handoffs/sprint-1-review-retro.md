# Sprint 1 — Review & Retrospective (Stage 0: Stabilization)

---

# 📊 Sprint Review (the product)

**Sprint Goal:** Make the live MVP safe for real players — no games lost on restart, no seat impersonation, results that persist.
**Outcome:** ✅ **Goal met** (pending final manual smoke ①–③ on the live stack).

## Delivered
| Task | Result |
|------|--------|
| TASK-001 Persistence | ✅ Per-action state writes (write-then-broadcast); UNIQUE `table_id`; survives restart |
| TASK-002 WS auth | ✅ HMAC per-seat token; no impersonation |
| TASK-003 REST lockdown | ✅ Host/seat authz, input validation, IP-fallback rate-limit |
| TASK-004 Scores | ✅ Per-game scoring with `game_seq`; atomic upsert; rematch-safe |
| TASK-005 Engine harness | ✅ 45 tests green in CI (incl. 4 regression guards) |
| TASK-006 Passwords | ✅ Create/join/enforce + 🔒 UI; no `password_hash` leak |

## Scope integrity
- **Committed:** 29 SP across 6 tasks. **Delivered:** all 6. Nothing dropped.
- All work maps to the PRD north star (Stage 0 of the commercial roadmap).

## Quality signal
- **11 issues caught pre-production:** QA-001…007, PM-001, WEB-001, DEPLOY-001.
- **0 escaped to production.** The gate worked as designed.
- Notable near-miss: DEPLOY-001 — code was correct but the live DB was stale (no UNIQUE key, missing `game_seq`). The staging sweep caught a DB that would have left the P0 exploitable and broken all score writes. Caught, fixed, verified.

## Exit condition remaining
- Manual functional smokes on the live stack: ① restart-survival, ② password flow + no-leak, ③ scores + rematch. (③ also harness-verified.)

---

# 🔄 Sprint Retrospective (the process)

## ✅ What went well
- **QA gate caught real, high-severity bugs before prod** — QA-001 (P0 duplicate-state restore), QA-006 (silent rematch data loss), DEPLOY-001 (stale DB). Discipline of "QA verifies before sign-off" repeatedly paid off.
- **Engine-first safety net** — 45-test harness built before the Stage 1 refactor; non-contiguous-seat and ordering regressions guard the exact bugs we fixed.
- **Strong technical decisions, well-reasoned** — write-then-broadcast over fire-and-forget; atomic UNIQUE-upsert over a COUNT guard; IP-fallback rate-limit. Each closed a class of bugs, not just an instance.
- **Deploy gate exists at all** — the `deploy-checklist.md` discipline turned "code complete" into "verified live," which is the only reason DEPLOY-001 didn't ship.

## ⚠️ What didn't go well
- **Bug-ID collisions across sessions** — `BUG-004`/`BUG-005` each minted twice; cost a reconciliation pass each time. Root cause: agents numbered independently + PM mistakenly minted into an agent's namespace.
- **"Done" claimed before verification** — TASK-001 and TASK-004 were each reported done, then QA found a P0/P1. "Code written" was being conflated with "done."
- **No real-environment testing in CI** — CI has only `pytest` (no MySQL, no PHP). Migrations and PHP syntax went unchecked until a manual staging sweep — which is how the stale DB and un-linted PHP slipped to the very end.
- **Migration fragility** — `dbDelta` silently fails to add UNIQUE indexes over existing duplicate rows; this wasn't anticipated and nearly shipped a broken schema.

## 🎯 Action items (carry into Stage 1)
1. **[DONE] Bug-ID convention** — area prefixes (`BE-/QA-/WEB-`), finder-owns-the-ID, `PM-` for PM-formalized items. Keep enforcing via the briefs.
2. **Add MySQL + PHP-lint to CI** — so schema migrations and `php -l` are verified automatically every push, not discovered in a manual sweep. *Highest-leverage fix.*
3. **Enforce Definition of Done** — a task is not "done" until QA-verified **and** staging-checked. No "done" on code-written alone.
4. **Document migration discipline** — `dbDelta` is unreliable for index/column changes on existing tables; use explicit migrations or a fresh recreate, and always verify with `SHOW INDEX`.
5. **Connection pooling** — fold into Stage 1 (FastAPI/SQLAlchemy) rather than per-action `aiomysql.connect()`.

## 📈 Metrics
- Tasks: 6/6 delivered · SP: 29/29 · Engine tests: 45 green
- Bugs found: 11 · Bugs escaped to prod: 0
- Process improvements adopted mid-sprint: 1 (bug-ID convention)
