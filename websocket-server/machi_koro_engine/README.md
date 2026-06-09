# machi_koro_engine

The headless Machi Koro **game engine** — pure rules, no transport or storage.
It depends only on the Python standard library and its own modules (no
`fastapi` / `aiomysql` / web / DB imports), so every backend imports the *same*
engine and the rules never fork. This is the Stage-2 keystone: the FastAPI backend
imports this package rather than reimplementing the rules.

## Layout
```
machi_koro_engine/
├── __init__.py      # public API (re-exported)
├── card_defs.py     # CARD_DEFS, LANDMARK_DEFS, symbol sets, SHARP_* pools
├── game_config.py   # GameConfig, build_config, config_for[_version], the configs
├── game_engine.py   # create_initial_state, handle_action, resolve_cards, …
└── tests/           # the 182-test characterization + feature suite (lives with the engine)
```

## Public API
```python
from machi_koro_engine import (
    create_initial_state, handle_action, resolve_cards, check_win,
    calculate_scores, advance_turn, seed,
    GameConfig, build_config, config_for, config_for_version,
    BASE_GAME, HARBOUR_GAME, BASE_SHARP_GAME, HARBOUR_SHARP_GAME, CONFIGS,
    CARD_DEFS, LANDMARK_DEFS,
)
```
Reach into the submodules (`machi_koro_engine.game_engine`, `.game_config`,
`.card_defs`) only for internals — e.g. the test suite does, for helpers like
`_draw_to_market` and `_set_interactive_phase`.

## Versions / modes (the config seam)
`config_for(base, sharp=False, variable_supply=None)` resolves the three
independent options into a `GameConfig`:
- **base**: `'basic'` | `'harbour'` (or a config name)
- **sharp**: layer the Millionaire's Row add-on (`"… + Sharp"`)
- **variable_supply**: the 10-face-up supply mode (`None` = default: on for Sharp,
  off otherwise; pass a bool to override)

The engine reads everything version-specific from the active `GameConfig`, so
adding a version is adding a config, not changing engine logic.

## Determinism
All randomness (dice, the Variable-Supply deck shuffle) goes through one seedable
`random.Random` via `seed(n)` — used by the tests for reproducible runs.

## Running the tests
From `websocket-server/` (the package's parent, on the import path):
```
python3 -m pytest        # 182 tests
```
`pytest.ini` sets `pythonpath = .` and `testpaths = machi_koro_engine/tests`.
