# Engine tests — TASK-005

Characterization suite for `game_engine.py`. It locks in the engine's **current**
behavior so the Stage 1 refactor can't silently change card math. Tests assert
what the code does today (not an idealized rulebook); any place where current
behavior is arguably non-standard is flagged in a comment but asserted as-is.

## Run

```bash
cd websocket-server
pip install -r requirements-dev.txt
pytest
```

Runs in CI via `.github/workflows/engine-tests.yml` on every push/PR touching
`websocket-server/`.

## Determinism

Two techniques keep rolls reproducible:

- **Direct `resolve_cards(state, roll)`** — exact card-payout math, no dice at all.
  Used for all per-card amount tests.
- **`force_rolls(...)` fixture** (`conftest.py`) — monkeypatches `roll_die` to yield
  a scripted sequence, for paths through `handle_action` (roll, harbor, tuna, reroll).

The `seed()` seam Backend added is exercised directly in `TestDeterminism`.

## Coverage (45 tests)

| Area | Cards / behavior |
|------|------------------|
| Blue Primary | wheat, ranch, forest, mine, apple, flower-garden, mackerel (±harbor); pays all owners |
| Green Secondary | bakery, convenience; cheese/furniture/farmers/flower-shop/food-warehouse multipliers |
| Red Restaurant | cafe, family, sushi(±harbor), hamburger, pizza; **counter-clockwise** order; coin-capped |
| Purple Major | stadium, tv-station, business-center, publisher, **tax-office rounding + 10+ gate** |
| Shopping Mall | +1 on bread (green) and cup (red) |
| City Hall | floor at 0 coins (fires even on the tuna income step) |
| Win | `check_win` on all landmarks; build-driven win |
| Tuna Boat | interactive roll + full harbor-prompt path |
| Determinism | `seed()` reproducibility; seeded `handle_action` roll |
| Build | spend+supply decrement, insufficient coins, purple max-per-player, wrong-seat ignored |

## Notes for the Stage 1 refactor

Behaviors these tests pin that a refactor must preserve (or consciously change):

- **City Hall fires during income resolution** even when other income arrives later
  in the same turn (e.g. the tuna path) — see `TestTunaBoat.test_tuna_full_path_*`.
- **Red restaurants resolve counter-clockwise** from the active seat; when the payer
  runs out of coins, earlier-in-order opponents are paid first.
- **Own cup/bread cards** don't pay their owner as Red income (Red only hits the
  active player's opponents).
