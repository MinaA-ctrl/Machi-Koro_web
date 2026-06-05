# Stage 1 — Engine Extraction · Sprint 2 Plan

> **Status (2026-06-05): PLANNED · ready to start.** Stage 0 (Stabilize) and Stage 0.5 (Frontend polish) are conditionally closed; their remaining items are owner-run manual checks on the live stack and **do not block Stage 1** (per `sprint-1-handoffs/stage-0-closeout.md`). Those smokes run **in parallel** at the owner's convenience.

> **North star:** `MachiKoro_FullProductPlan.docx` / `MachiKoro_PRD.md`. Stage 1 is PRD critical-rule #2 — *"the tested engine before Stages 2–8; never skip it again."*

## 🎯 Stage 1 goal
A headless, version-agnostic game engine package `machi_koro_engine/`, driven by `GameConfig` (Basic / Harbour / Sharp), with deterministic seedable RNG, **i18n-ready structured output**, 100+ unit tests and ≥80% line coverage. Today the rules live embedded in the WebSocket server as Harbour-only logic.

Stage 1 is a **2-sprint stage**. This document is **Sprint 2 = slice 1 of 2**.

## ⚖️ PM scope note
- **Behavior preservation is the prime directive.** The 45-test characterization harness (Stage 0 TASK-005) must stay green through extraction. Any diff in card math is a regression, not an improvement.
- **i18n-readiness is a contract, not a feature.** No translation happens this stage (no UI yet). The engine simply must emit *structured, keyed* output instead of English sentences, so Stage 3 localization is "add a locale file," not "rip strings out of the engine." (Retires PRD risk *"i18n retrofitted late."*)
- **Don't over-scope.** Engine only. No FastAPI, no Postgres, no React — those are Stages 2/3.

**Sprint 2 Goal:** *Lift the rules out of the WebSocket server into a standalone, seedable, i18n-ready engine package — version-agnostic via GameConfig, with Harbour preserved bit-for-bit and Basic added — and close the Sprint-1 CI gap.*

**Scope:** ~29 SP · Owner: **Backend** · QA: engine test suite + harness-green gate · Velocity target: 30.

**Task index:**
- TASK-101 — Sharp card-list spike (Must · 3 SP) — *runs first, unblocks Sprint 3*
- TASK-102 — Extract engine to `machi_koro_engine/` (Must · 8 SP)
- TASK-103 — `GameConfig` abstraction (Must · 8 SP)
- TASK-104 — Basic version config (Should · 5 SP)
- TASK-106 — Seedable RNG for dice (Must · 2 SP)
- TASK-108 — CI: MySQL service + `php -l` (Must · 3 SP) — *carry-forward #1 from retro*

> **Process carry-forward (0 SP):** enforce the tightened Definition of Done — "done" = QA-verified **and** staging/harness-checked, never code-written alone (Sprint-1 retro action #3).

---

## TASK-101 — Spike: confirm the Sharp card list & rule deltas
**Type:** Spike · **Priority:** Must · **SP:** 3 · **Assignee:** Backend · **Dependencies:** —

**As the** developer
**I want** a confirmed, canonical Sharp (Millionaire's Row / "Sharp") card + landmark list with its rule differences
**So that** Stage 1.2 (Sprint 3) can build the Sharp `GameConfig` from fact, not assumption — this is flagged in the PRD risk table as a **blocker, not an assumption**.

**Acceptance Criteria:**
- [ ] Canonical card list captured: every establishment (name, ID, cost, activation roll(s), icon/type, payout rule) and every landmark (name, ID, cost, effect)
- [ ] Rule deltas vs. Harbour documented explicitly (any new activation mechanics, win condition changes, starting-hand/deck differences, two-dice/reroll interactions)
- [ ] Each card mapped to a **stable string ID** (the key the engine and future locale files use)
- [ ] Cross-checked against `MachiKoro CardReference copy.xlsx` and the FullProductPlan; discrepancies listed
- [ ] Output committed as `sprint-2-handoffs/sharp-card-reference.md` (machine-translatable into a GameConfig)
- [ ] **Decision recorded:** if Sharp cannot be confirmed with confidence, recommend descoping Sharp from Stage 1 and shipping Basic + Harbour (engine still version-agnostic, Sharp added later)

**Technical notes:** Pure research/documentation task — no code. Sequenced **first** in the sprint precisely so Sprint 3's Sharp config (TASK-105) is never blocked waiting on it.

---

## TASK-102 — Extract the engine into `machi_koro_engine/`
**Type:** Chore (refactor) · **Priority:** Must · **SP:** 8 · **Assignee:** Backend · **Dependencies:** —

**As the** developer
**I want** the pure game logic moved out of the WebSocket server into a standalone, importable package with a clean API
**So that** every later stage (FastAPI, AI, tests) wires to one headless engine instead of logic tangled in the transport layer.

**Acceptance Criteria:**
- [ ] New package `machi_koro_engine/` contains all rules/state-transition logic, **no transport, DB, or WebSocket imports**
- [ ] Clean public API: create a game from a config, `apply_action(state, action) -> new_state`, `get_state()`, legal-move/validation surface, terminal/winner detection
- [ ] Engine is **pure & server-authoritative**: deterministic given (state, action, RNG); no network/IO side effects inside the engine
- [ ] **i18n-ready output (contract):** the engine emits **structured, keyed events** — e.g. `{type: "earn_income", card_id: "wheat_field", seat: 2, amount: 1}` — **never pre-formatted English sentences.** Cards/landmarks referenced by **stable ID**, not display name.
- [ ] The Stage-0 **45-test characterization harness stays 100% green** against the extracted engine — **zero behavior change**
- [ ] WebSocket server refactored to *call* the engine; no rules logic remains duplicated in the server
- [ ] No regression in a live local game (manual smoke after wiring)

**Definition of Done:**
- [ ] Code written and reviewed
- [ ] 45-test harness green in CI + engine imports with no transport deps
- [ ] WS server still plays a full game locally (staging-checked)
- [ ] Documentation: short `machi_koro_engine/README.md` describing the API + event-output contract

**Technical notes:** This is a *move + adapt*, not a rewrite — preserve algorithms exactly. The structured-event contract is the single most important forward-looking decision here (it's what makes Stage 3 i18n cheap and Stage 4 history-replay possible). Land the event schema before the rest of the extraction so everything emits through it.

---

## TASK-103 — `GameConfig` abstraction (version = config, engine = version-agnostic)
**Type:** Feature · **Priority:** Must · **SP:** 8 · **Assignee:** Backend · **Dependencies:** TASK-102

**As a** host
**I want** the engine to take a version as a `GameConfig` object
**So that** Basic / Harbour / Sharp are *data*, and the engine code never hard-codes one version's rules.

**Acceptance Criteria:**
- [ ] A `GameConfig` defines a version's full ruleset as data: establishment set, landmark set, starting hand, deck/supply composition, win condition, and rule toggles (e.g. Harbour-specific mechanics)
- [ ] Engine reads **all** version-specific behavior from the active `GameConfig` — **no `if version == "harbour"` branches** in core logic
- [ ] **Harbour** is expressed as a `GameConfig` and reproduces today's behavior exactly (45-test harness green under the Harbour config)
- [ ] Card/landmark definitions carry the **stable ID + i18n key** (display name/effect text are NOT baked into the engine — they're future locale content keyed off the ID)
- [ ] Config is validated on load (e.g. no duplicate IDs, deck counts sane, win condition present)
- [ ] Adding a new version requires **only** a new config + its cards, no engine code changes (proven by TASK-104)

**Definition of Done:**
- [ ] Code written and reviewed
- [ ] Harbour-config run is harness-green (behavior identical)
- [ ] Coverage on config-loading + a version-agnostic engine path
- [ ] Doc: how to author a new `GameConfig`

**Technical notes:** Design the config seams against **two** versions this sprint (Harbour + Basic via TASK-104) so the abstraction is validated by real divergence, not a single example. Resist encoding Harbour assumptions as defaults.

---

## TASK-104 — Basic version `GameConfig`
**Type:** Feature · **Priority:** Should · **SP:** 5 · **Assignee:** Backend · **Dependencies:** TASK-103

**As a** host
**I want** to create a game in the **Basic** ruleset
**So that** the platform supports the entry-level version and proves the `GameConfig` abstraction with a second real version.

**Acceptance Criteria:**
- [ ] Basic establishment set, landmark set, starting hand, supply, and win condition encoded as a `GameConfig` (no engine code changes — config only)
- [ ] Each Basic card has a stable ID + i18n key consistent with the Harbour ID scheme
- [ ] A full Basic game plays start-to-finish in the engine (programmatically) and reaches a valid winner
- [ ] Basic-specific rules differing from Harbour are correctly applied (e.g. landmark set / no harbour mechanics)
- [ ] Dedicated Basic unit tests (card activations, win condition) added toward the 100+ suite

**Definition of Done:**
- [ ] Code written and reviewed
- [ ] Basic test set green in CI; coverage counted toward the Stage-1 ≥80% goal
- [ ] No regression to Harbour (harness still green)

**Technical notes:** Basic ⊂ Harbour in most respects, so this primarily exercises *omission* (fewer cards/landmarks, no harbour rules). If authoring Basic forces an engine code change, that's a TASK-103 abstraction leak — fix it there, not with a special-case.

---

## TASK-106 — Seedable, injectable RNG for dice
**Type:** Chore · **Priority:** Must · **SP:** 2 · **Assignee:** Backend · **Dependencies:** TASK-102

**As the** developer
**I want** the engine's dice/randomness to come from a seedable, injectable RNG
**So that** games are deterministic in tests (PRD: "deterministic, seedable RNG for testing") and auditable in production (PRD: server-side dice, logged events — RNG/fairness risk row).

**Acceptance Criteria:**
- [ ] All randomness (dice rolls, any shuffles) flows through a single injectable RNG source — no bare `random.*` calls scattered in logic
- [ ] Engine accepts a seed (or RNG instance) at game creation; same seed + same actions ⇒ identical game
- [ ] Production path uses a proper unseeded/secure default; tests inject a fixed seed
- [ ] At least one deterministic end-to-end test asserts a full seeded game is reproducible

**Definition of Done:**
- [ ] Code written and reviewed
- [ ] Determinism test green in CI
- [ ] Harness still green (rolls produced identically where it pins them)

**Technical notes:** Land this early — it makes every subsequent engine test simpler and is a prerequisite for trustworthy multiplayer dice later.

---

## TASK-108 — CI: add MySQL service + PHP lint
**Type:** Chore (DevOps) · **Priority:** Must · **SP:** 3 · **Assignee:** Backend / DevOps · **Dependencies:** —

**As the** team
**I want** CI to spin up MySQL and run `php -l` on every push
**So that** schema migrations and PHP syntax are verified automatically — not discovered in a manual staging sweep (root cause of the DEPLOY-001 near-miss; retro action #2, *highest-leverage fix*).

**Acceptance Criteria:**
- [ ] CI workflow adds a **MySQL service container**; migration/bootstrap runs against it on every push
- [ ] CI runs **`php -l`** across all plugin PHP files; a syntax error fails the build
- [ ] Existing `pytest` job (incl. the 45-test harness) still runs and is required
- [ ] A deliberately broken migration / PHP syntax error **fails** CI (negative test confirms the gate works)
- [ ] Migration discipline note added (retro action #4): `dbDelta` is unreliable for index/column changes on existing tables — use explicit migrations + verify with `SHOW INDEX`

**Definition of Done:**
- [ ] Workflow committed and green on a real push
- [ ] Demonstrated red on an intentional break, then green when reverted
- [ ] `sprint-1-handoffs/deploy-checklist.md` updated to reference the now-automated checks

**Technical notes:** Independent of the engine tasks — can run in parallel by whoever has CI context. Closes the single biggest process gap from Sprint 1.

---

## Sequencing & ownership
- **Owner: Backend** for all engine tasks; TASK-108 can be done in parallel (CI, no engine coupling).
- **Order:** TASK-101 (spike, first — unblocks Sprint 3) ∥ TASK-108 (CI, parallel) → TASK-102 (extract; lands the event schema first) → TASK-103 (GameConfig, Harbour parity) → TASK-104 (Basic, validates the abstraction). TASK-106 (RNG) folds into TASK-102's window.
- **The harness is the gate:** 102 and 103 are not "done" until the 45-test characterization suite is green under the extracted/config-driven engine. No exceptions (DoD enforcement, retro #3).
- **Parked owner checks run in parallel** (non-blocking): Stage-0 smokes ①–③ + Stage-0.5 cross-viewport QA pass.

## Sprint 3 preview (Stage 1 finish)
- **TASK-105 — Sharp `GameConfig`** (8 SP) — unblocked by the TASK-101 spike.
- **TASK-107 — Grow suite to 100+ tests, ≥80% coverage** across Basic/Harbour/Sharp (13 SP) + hardening buffer.
- Stage-1 exit = all three versions playable through one engine, harness + suite green, coverage gate met → clears Stage 2 (Backend migration).

## Risks
| Risk | P | Impact | Mitigation |
|------|---|--------|------------|
| Extraction silently changes card math | High | High | 45-test harness must stay green through 102/103; treat any diff as a regression |
| Sharp underspecified → blocks Sprint 3 | Med | Med | TASK-101 spike runs first; if unconfirmable, descope Sharp from Stage 1, ship Basic+Harbour |
| `GameConfig` under-abstracts (Harbour assumptions leak) | Med | Med | Validate seams against two versions (Harbour + Basic) this sprint, not one |
| Engine bakes English into output → costly i18n retrofit | Med | High | Structured/keyed event contract in TASK-102; cards by stable ID, no display strings in engine |
| CI MySQL/PHP work expands | Low | Med | Time-boxed at 3 SP; parallel owner; negative test proves the gate, then stop |
