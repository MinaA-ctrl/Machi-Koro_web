# Sprint 1 — Stage 0: Stabilization (Sprint Packet)

> Self-contained packet for the Machi Koro stabilization sprint. Each `*.md` here is a handoff brief to paste into the matching specialist agent's session.
> Full context: see `../MachiKoro_PRD.md` (north-star PRD) and `../MachiKoro_FullProductPlan.docx`.

## 🎯 Sprint Goal
Make the **live** MVP safe for real players: **no games lost on restart, no seat impersonation, locked-down REST, and persisted results.**

**Methodology:** Scrum · 2-week sprint · Story Points · MoSCoW · committed **29 SP**.

## 👥 Team this sprint
Backend (lead) · QA (gate) · Web (cameo) · PM (coordination).
Not needed for Stage 0: ~~Designer~~, ~~Mobile-dev~~ — no blockers.

## 🗂️ Task → owner

| Task | Title | Owner | Support | Pri | SP | Brief |
|------|-------|-------|---------|-----|----|-------|
| 001 | Persist state per action | 🔧 Backend | 🧪 QA | Must | 8 | `backend.md` |
| 002 | Authenticate WebSocket | 🔧 Backend | 🧪 QA | Must | 5 | `backend.md` |
| 003 | Lock down REST | 🔧 Backend | 🧪 QA | Must | 3 | `backend.md` |
| 004 | Persist scores + leaderboard | 🔧 Backend | 🧪 QA | Must | 5 | `backend.md` |
| 005 | Engine test harness | 🧪 QA | 🔧 Backend (RNG seam) | Must | 5 | `qa.md` |
| 006 | Table passwords | 🔧 Backend | 🎨 Web (prompt UI) | Should | 3 | `backend.md` + `web.md` |

**Cut line if capacity is tight:** TASK-006 (only "Should"). Everything else is a Must — each is a data-loss or security exposure on a *live* product.

## 🏷️ Bug-ID convention (all agents)
- **Prefix your own findings by area:** `BE-001`, `QA-001`, `WEB-001` — increment within your own namespace.
- **Prefix = FINDER, not FIXER.** A fix references the existing ID; never mint a new number for a bug you only fixed.
- **PM owns the canonical master log** (`bugs.md`) and maps/records; never renumbers.
- **PM never mints IDs in an agent's namespace** — PM-formalized or cross-cutting items use a `PM-` prefix (`VERIFY-` for verification-only).
- Reference bugs by prefixed ID in handoffs, commits, and re-verify loops.

## 🔗 Dependency map
```
Backend RNG seam ───────────► QA TASK-005 (deterministic tests)
Backend user_id threading ──► Backend TASK-004 (score attribution)
Backend TASK-006 (API) ─────► Web TASK-006 (password UI)
Every Backend fix ──────────► QA verification TC (as it lands, not at the end)
```
Suggested order: **001 → 002** (highest-risk Musts) → RNG seam → 003/004 → 006. QA builds 005 in parallel from the RNG seam onward.

## ▶️ How to run
Open one session per agent and paste the matching brief:
```bash
cd ~/Programming\ projects/Vibe_coding/Claude_Antropic/AGENTS-en/backend-developer && \
  claude --add-dir ~/Programming\ projects/Vibe_coding/Claude_Antropic/Machi\ Koro\ project   # paste backend.md

cd ~/Programming\ projects/Vibe_coding/Claude_Antropic/AGENTS-en/qa-tester && \
  claude --add-dir ~/Programming\ projects/Vibe_coding/Claude_Antropic/Machi\ Koro\ project   # paste qa.md

cd ~/Programming\ projects/Vibe_coding/Claude_Antropic/AGENTS-en/web-developer && \
  claude --add-dir ~/Programming\ projects/Vibe_coding/Claude_Antropic/Machi\ Koro\ project   # paste web.md
```

## ✅ Definition of Done (every task)
- [ ] Code written & reviewed
- [ ] Tests written (>80% on new logic) — coordinate with QA
- [ ] Deployed to the staging Docker stack
- [ ] Docs/README updated (e.g. new `MK_WS_SECRET` env var)

## 🏁 Sprint exit criteria
- [ ] A forced WS-server restart mid-game loses **no** in-progress games (001)
- [ ] No socket can act as a seat it doesn't own (002)
- [ ] No unauthorized REST host actions; table-create rate-limited (003)
- [ ] Registered players' results land in `wp_mk_scores`, exactly once (004)
- [ ] Engine pytest suite green in CI, ≥20 deterministic tests (005)
- [ ] Protected tables enforce passwords end-to-end (006)
