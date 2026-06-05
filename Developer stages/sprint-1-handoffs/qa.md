# Handoff → QA Engineer · Sprint 1 (Stage 0: Stabilization)

> Paste this into a `qa-tester` Claude session. Code lives in `~/Programming projects/Vibe_coding/Claude_Antropic/Machi Koro project`.
> The game engine is `websocket-server/game_engine.py` (+ `card_defs.py`); the WS server is `websocket-server/main.py`. Stack runs via `docker-compose.yml`.

## Sprint goal (your part)
Stand up the **engine safety net** and **verify every backend fix**. You own quality for a live product about to take real players. Note: the engine currently has **zero tests** — your harness is also the down-payment on Stage 1's required 100+ test suite.

## TASK-005 — Engine characterization test harness (Must · 5 SP, you own it)
**Goal:** a `pytest` suite that locks in the *current* engine behavior (characterization, not redesign) so the upcoming Stage 1 refactor can't silently break card math.

**Setup:**
- `pytest` running in the `websocket-server` container / CI (GitHub Actions).
- **Deterministic dice:** Backend is adding a seedable RNG seam (`_rng` / `seed()`) in `game_engine.py`. Use it so rolls are reproducible. (Coordinate with Backend — this is your unblocker.)
- Build states via `create_initial_state(...)` and drive them with `handle_action(state, seat, msg)`.

**Coverage — at least 20 tests across:**
- [ ] Each card type's payout: Blue (wheat/ranch/forest/mine/apple/flower/mackerel), Green (bakery/convenience/cheese/furniture/farmers/flower-shop/food-warehouse), Red (cafe/family/sushi/hamburger/pizza), Purple (stadium/tv/business/publisher/tax)
- [ ] Red restaurants resolve **counter-clockwise** from active (order matters when payer runs out of coins)
- [ ] Shopping Mall +1 bonus on cup/bread cards
- [ ] Tax Office rounding (half, rounded down, only opponents with 10+)
- [ ] City Hall floor (active player at 0 coins gets 1)
- [ ] Win condition fires immediately when all landmarks built (`check_win`)
- [ ] Cheese/Furniture/Farmers/Flower-shop/Food-warehouse multipliers (count-based)
- [ ] Tuna Boat + Harbor interactive roll path

**AC:**
- [ ] pytest green against current behavior, runs in CI
- [ ] Deterministic (seeded) rolls
- [ ] ≥20 tests covering the above

### Regression tests folded in from TASK-001 bug fixes (required for TASK-001 full DoD)
These guard the BUG-001/002/003 fixes so they can't silently regress. They live in this suite + CI:
- [ ] **TC restart-survival (E2E):** game → restart container → reconnect → assert identical state
- [ ] **TC concurrent-reconnect (regression, guards QA-001):** two clients reconnect same tick → exactly one `wp_mk_game_states` row per `table_id`
- [ ] **TC action-vs-auto-win ordering (regression, guards QA-002):** action during grace window → finished snapshot is the last DB write; no swallowed exceptions
- [ ] **TC non-contiguous seats (regression, guards QA-004):** build state with seats {0,5,6} (post-kick) and drive a full turn → engine resolves turn order, red-card direction, and win by **seat value**, not 0-based index
> Note: TASK-001 is verified by QA; its DoD "tests" box closes when these three are green in CI under TASK-005.

## Verification test plan — backend fixes (TC format)
Write and run these as Backend lands each task. Use your standard TC format; priorities below.

### TC — TASK-001 (Persistence) · P0
- **Steps:** Start a 2-player game, take several actions (roll/buy), restart the `websocket` container, reconnect.
- **Expected:** Game resumes with identical coins, cards, landmarks, `active_seat`, `phase`. No reset to initial state.

### TC — TASK-002 (WS auth) · P0
- **Steps:** Attempt to connect to `/ws/{code}/game/{seat}` (a) with no token, (b) with a token for a different seat, (c) with an expired token.
- **Expected:** All rejected/closed. Only a valid token for the matching seat connects and can act.

### TC — TASK-003 (REST lockdown) · P1
- **Steps:** Call `kick`/`start`/`rename` as a non-host identity; spam `create_table`.
- **Expected:** 403 for unauthorized host actions; rate-limit kicks in on table spam; malformed inputs return consistent errors.

### TC — TASK-004 (Scores) · P1
- **Steps:** Finish a game with mixed registered + guest players; also trigger the auto-win path (everyone else leaves); finish then reconnect.
- **Expected:** Exactly one `wp_mk_scores` row per registered player, zero for guests, **no duplicates** across the win and auto-win paths.

### TC — TASK-006 (Passwords) · P2
- **Steps:** Create protected table; join with correct, wrong, and no password.
- **Expected:** Correct joins; wrong/missing → 403; listings show 🔒.

## Test pyramid for this sprint
- **Unit (many):** TASK-005 engine tests.
- **Integration/API (some):** REST auth/validation (TASK-003), score writes (TASK-004).
- **E2E (few, critical):** restart-survival (001) and seat-auth (002) — the two P0 flows.

## Definition of Done
- [ ] All P0/P1 test cases written and passing against staging
- [ ] Engine suite in CI, ≥20 tests, deterministic
- [ ] Any bug found logged in your standard bug-report format and handed to Backend via PM
