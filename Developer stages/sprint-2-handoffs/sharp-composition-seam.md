# Sharp Composition Seam — contract for Phases B/C/D

> **Status (2026-06-06): Phases A–C2 SHIPPED — all 13 Sharp cards exist (engine/
> config only).** Stage 1, slice 2, branch `Stage-1_add_base`. No DB, no UI.
> **160 tests green** (`cd websocket-server && python3 -m pytest -q`).
> A: composition + 6 Tier-1. B: Renovation + Winery & Cleaning Company. C1: Loan
> Office, Park, Tech Startup. C2: Demolition & Moving Company (see "Phase C2").
> The Sharp pool is **complete at 13 cards**. Remaining Sharp work is **Phase D**
> (DB `sharp` flag + UI prompts + browser QA) — engine handlers for every
> interactive card already exist and are test-driven.

Sharp (Millionaire's Row) is a **composable add-on, not a third version**: a
`+ Sharp` flag that layers the MR cards onto either base. This note is the seam
the later phases build on — keep it stable.

## The composition API (`game_config.py`)

- **`GameConfig`** gained a `sharp: bool = False` field. A config is fully
  identified by **(base, sharp)**. Plain Basic/Harbour keep `sharp=False`.
- **`build_config(base, sharp=False) -> GameConfig`** — the composer.
  - `sharp=False` returns the base **unchanged** (same object — identity preserved).
  - `sharp=True` returns `replace(base, name="<Base> + Sharp",
    establishment_ids=base.establishment_ids + SHARP_CARD_IDS, sharp=True)`.
  - Landmarks, starting hand, and starting coins are the base's — **Sharp adds no
    landmarks**, and the landmark-count conditionals are base-agnostic (they count
    constructed landmarks, so 4-landmark Basic and 6-buildable Harbour both work).
- **Canonical singletons:** `BASE_SHARP_GAME` ("Basic + Sharp"),
  `HARBOUR_SHARP_GAME` ("Harbour + Sharp"). Resolvers return these so round-trips
  compare equal by identity.

### No-leakage guarantee
Harbour is now derived as `HARBOUR_ESTABLISHMENTS = tuple(cid for cid in CARD_DEFS
if cid not in SHARP_CARD_IDS)`. The Sharp cards live in `CARD_DEFS` (so the engine
can resolve them) but are **excluded from plain Basic/Harbour** — Sharp is opt-in
only. The pool is the tuple `SHARP_CARD_IDS = SHARP_TIER1_IDS + SHARP_PHASE_B_IDS
+ SHARP_PHASE_C1_IDS + SHARP_PHASE_C2_IDS` (each phase just extended a tuple —
config/leakage code keys off `SHARP_CARD_IDS`). The pool is now complete.
Counts (13 Sharp cards): Basic 15, Harbour 25, **Basic+Sharp 28, Harbour+Sharp 38**.

## The round-trip / rematch seam (`config_for_version`, `config_for`)

Two resolvers, both returning the singletons:

- **`config_for_version(version)`** — string → config. Now also recognizes the
  composed names ("Basic + Sharp", "Harbour + Sharp"), case/space-insensitive.
  This is what **rematch** uses today: a finished game stores its config name in
  `state['version']`; `main.py` rebuilds via `config_for_version(state['version'])`,
  so a Sharp game round-trips. Unknown/missing → Harbour (unchanged back-compat).
- **`config_for(base, sharp=False)`** — the **(base, sharp) pair** → config. This
  is the seam **Phase D** persists against: store `(game_version, sharp)`, resolve
  with `config_for(game_version, sharp)`. `base` may be a key ('basic'/'harbour')
  or a name; it's normalized through `config_for_version`.

### Phase D wiring (when you get there)
- Add a `sharp TINYINT(1) NOT NULL DEFAULT 0` column via a **guarded `mk_migrate`
  ALTER** + bump `MK_DB_VERSION` (see `migration-discipline.md`).
- At both `create_initial_state` call sites in `main.py` (table start + rematch),
  switch `config_for_version(...)` → `config_for(game_version, sharp)`.
- Rematch already round-trips on the name even before that switch, so the two can
  land independently.

## Tier-1 cards (`card_defs.py` + `game_engine.resolve_cards`)

`SHARP_TIER1_IDS` is the Phase-A pool (`SHARP_PHASE_B_IDS` adds Phase B; Phase C
appends the rest, all folded into `SHARP_CARD_IDS`). The
`landmarks_built(player)` helper (`game_engine.py`) is the shared primitive — it
counts built landmarks **excluding City Hall** (same rule `calculate_scores` uses,
which was refactored to call it). Effects:

| Card | Dice | Section | Effect |
|---|---|---|---|
| Vineyard | 7 | blue (anyone) | +3 flat, per copy |
| Corn Field | 3–4 | blue (anyone) | +1/copy **iff owner `landmarks_built ≤ 1`** |
| General Store | 2 | green (your turn) | +2/copy **iff active `landmarks_built ≤ 1`** |
| Soda Bottling Plant | 11 | green (your turn) | +1/copy per Red establishment across **all** players (owner's reds included) |
| French Restaurant | 5 | red (opp turn) | take 5/copy from roller **iff roller `landmarks_built ≥ 2`** (capped at their balance) |
| Private Club | 12–14 | red (opp turn) | take **all** the roller's coins **iff roller `landmarks_built ≥ 3`** (extra copies redundant) |

### Symbol choice (deliberate)
Tier-1 symbols are **cosmetic and decoupled**: `grape, grain, store, factory,
restaurant` — none are `cup`/`bread` (so Shopping Mall never applies) and none
reuse `wheat` (so Farmers Market doesn't count them). If a later phase needs a
real symbol interaction (e.g. a Tier-2 card keying off Vineyard), wire it by
**card id**, not by reviving a load-bearing symbol, unless you also update the
affected mechanics + tests.

## Renovation model (Phase B) — contract for Phase C

The first Sharp mechanic that needs **new game state**. Phase C's Demolition
(landmark-loss) and others may reuse this; keep it stable.

### State
`player['renovation'] = {card_id: closed_copies}` — added to every player in
`create_initial_state` (so it persists via the existing per-action JSON save/load;
there's a test for the round-trip). Helpers in `game_engine.py`:
`closed_copies`, `active_copies` (= owned − closed), `close_for_renovation`,
`_reopen`.

### The rule (one place: top of `resolve_cards`, "section 0")
A closed copy **skips exactly one activation, then reopens.** When a card's number
comes up:
1. compute `paying[(seat, card_id)] = owned − closed` (the copies that pay this roll),
2. reopen the closed copies (`_reopen`) — their skipped activation is now spent.

Every payout section (red/blue/green/purple) then multiplies by `act_of(...)`
(the paying count) instead of raw `count`, and `continue`s when `act <= 0`. With
nothing renovated, `act == owned` and behavior is byte-identical to Phase A — this
is why the 98 prior tests stayed green.

### Decision — per-COPY count (not per-stack)  ✅ chosen
We track a **closed-copy count per (player, card_id)**, so copies renovate
independently — matching the physical per-card tokens. Worked example with 2
Wineries, 1 already closed, on a roll of 9: the open copy pays and closes, the
closed copy reopens → exactly 1 closed afterward (test:
`test_multi_copy_independent_when_mixed`). A per-stack model (all-or-nothing per
type) was the alternative; rejected because it can't represent that mixed state.

### The two cards
- **Winery** (`winery`, green, dice 9): each *active* copy pays `6 × Vineyards
  owned`, then those copies `close_for_renovation`. Closes even when it pays 0
  (0 Vineyards). Next roll-9 reopens them, paying 0.
- **Cleaning Company** (`cleaning_company`, Purple Major, dice 8, max 1):
  **interactive**, mirroring TV Station / Business Center.
  - `_set_interactive_phase` adds a `cleaning_company` branch: if the active player
    owns it and there are valid targets, set `phase='cleaning_company'` and
    `pending_prompt = {'type':'cleaning_company', 'targets': [...]}`.
  - `_cleaning_targets(state)` = non-Major types with ≥1 **open** copy anywhere.
  - New `handle_action` event **`cleaning_company_pick {card_type}`**: validates
    server-side (real card, **not** Purple Major, present as an open copy), closes
    **all open copies of that type across all players**, and the active player
    collects **1 coin per copy closed** (from the bank). Then it threads on via
    `_set_interactive_phase(..., cleaning_done=True)`.

### ✅ Resolved decision (PM ruling, 2026-06-06): renovated cards still count
"Count" effects on a card under renovation: a closed card is **still owned** for
*other* cards' counting effects — it's in hand, it just doesn't function.
Concretely: **Winery counts a renovated Vineyard**, and **Soda Bottling Plant
counts a renovated Red** toward its total. Renovation suppresses a card's *own*
activation, not its ownership. This is implemented via `card_count(...)` (owned)
rather than `active_copies(...)` in those effects, and locked by tests
(`test_winery_counts_renovated_vineyard`, `test_soda_counts_renovated_red`).
Phase C "count" cards should follow the same rule (count owned, not open).

## Phase C1 — Loan Office, Park, Tech Startup (contract for C2/D)

Three cards, all with the three PM-locked defaults baked in. Pool grows to 11.

### Loan Office (`loan_office`, green, dice 5–6, cost 0)
- **Build-time payout:** the `build` handler gives **+5** from the bank right after
  a `loan_office` purchase (only special-cased card in the build path).
- **Negative activation (your turn):** in `resolve_cards`' green section, pays the
  bank **2 per active copy**, **floored at 0** (`min(coins, act*2)`) — locked
  default. It's the first card with a *negative* activation; it `continue`s before
  the positive-payout block. Renovation-aware (uses `act_of`).

### Park (`park`, Purple Major, dice 11–13, cost 3, max 1)
- In `resolve_cards`' purple section: pool every player's coins, `share = total //
  n`, and the **remainder goes to the active player** (locked default). Resolves
  *after* income (red/blue/green run first), so it redistributes post-income totals.
  Per-player deltas are reported as Park gains/losses.

### Tech Startup (`tech_startup`, Purple Major, dice 10, cost 1, max 1)
- **Persistent state:** `player['investments'] = {card_id: coins}` (added to every
  player in `create_initial_state`, persists via save/load like `renovation`).
- **Invest action:** new `handle_action` event **`tech_startup_invest`** — optional,
  on your turn, **during the `build` phase**, **at most once per turn** (gated by
  `state['tech_invest_used']`, reset in `advance_turn` *and* the Amusement-Park
  extra-turn branch). Moves 1 coin from the player onto the card.
- **Activation:** when the active player rolls 10, **each opponent pays them the
  total invested** (clamped to each opponent's balance). The investment **persists**
  — it is *not* cleared on activation (locked default).
- Not interactive (no prompt): invest is a proactive client action; activation is
  automatic. So `_set_interactive_phase` is unchanged this phase.

## Phase C2 — Demolition Company & Moving Company (finale)

Both are interactive (your turn), Green Secondary, dice 4 / 9–10, cost 2. The
number of demolitions/gives equals the card's **active (non-closed) copies**.

### Landmark-loss invariant (Demolition Company)
A built landmark goes **built → unbuilt** — the first time the engine breaks
"landmarks only increase." Audited and safe because both readers recompute from
state every call:
- `check_win` = `all(lm['built'] …)` on the active player — a demolished landmark
  makes it `False`; win is only ever checked in the build handler, never during
  demolition, so a demolisher can't be flagged a winner.
- `calculate_scores`/`landmarks_built` count current built flags.
A demolished landmark is rebuildable via the normal build path (and can then win).
Tests: `test_demolisher_is_not_a_winner_game_continues`,
`test_demolished_landmark_can_be_rebuilt_and_win`.

- **Demolition:** demolish one own **built, non-City-Hall** landmark per active
  copy, **+8 per actual demolition only**. Mandatory when a demolishable landmark
  exists (you only choose which); **no demolishable landmark → does nothing (no
  +8)**. City Hall can never be demolished. Auto-resolves when there's exactly one
  demolishable landmark (no real choice); otherwise prompts. Handler
  **`demolition_pick {landmark_id}`**, validated server-side (active's, built, not
  City Hall). Multi-copy demolishes up to N, capped by available.
- **Moving:** give one own **non-Major** establishment to another player per active
  copy, **+4 each**. Moving Company itself is non-Major, so it's giveable.
  **No giveable card or no other player → does nothing.** Handler
  **`moving_company_pick {card_id, target_seat}`**, validated (owned, non-Major,
  real other player). `_remove_card` clamps the given card's renovation count to
  what remains; the receiver gets an open copy.

### Renovation timing (important seam detail)
`resolve_cards` "section 0" reopens renovated copies *before* `_set_interactive_phase`
runs, so the phase can't recompute active counts for these green cards. resolve_cards
therefore **stashes** the pre-reopen active counts in
`state['interactive_active_copies']`, read via `_interactive_copies(...)`. This is
why a card closed for renovation correctly fires 0 times on its first matching roll
(`test_renovation_skips_one_activation`, `test_renovation_limits_gives_to_active_copies`).

### Interactive-phase chain (full, established order)
`_set_interactive_phase`: TV Station → Cleaning Company → Business Center →
**Demolition → Moving** → Tuna → Build. Each step has a `*_done` flag so a handler
resumes the chain past itself. Multi-pick cards (Demolition, Moving) track
`remaining` in `pending_prompt` and re-prompt via `_resume_demolition`/`_resume_moving`.

## Out of scope — only Phase D + E remain
No DB column yet (**Phase D**: add a `sharp` column via guarded `mk_migrate` + bump
`MK_DB_VERSION`, switch `main.py` to `config_for(game_version, sharp)`, build the
frontend prompts for every interactive card — TV/Business Center/Cleaning/Demolition/
Moving picks + the Tech Startup invest button — and do real-browser QA). Variable
Supply is **Phase E** (deferred to the Stage 1 capstone). See `sharp-plan.md`.
