"""Machi Koro game engine — headless, importable, transport/DB-agnostic.

Pure rules: state creation, dice/card resolution, win/scoring, and the version
config seam (Basic / Harbour / +Sharp / Variable Supply). Depends only on the
Python stdlib and its own modules — no web/transport/DB imports — so any backend
(the FastAPI WS server today, the Stage-2 backend tomorrow) imports the same engine
and the rules never fork.

Public API is re-exported here; reach into the submodules
(`machi_koro_engine.game_engine`, `.game_config`, `.card_defs`) only for internals
(e.g. tests).
"""

from .card_defs import CARD_DEFS, LANDMARK_DEFS

from .game_config import (
    GameConfig,
    build_config,
    config_for,
    config_for_version,
    BASE_GAME,
    HARBOUR_GAME,
    BASE_SHARP_GAME,
    HARBOUR_SHARP_GAME,
    CONFIGS,
)

from .game_engine import (
    create_initial_state,
    handle_action,
    resolve_cards,
    check_win,
    calculate_scores,
    advance_turn,
    seed,
)

__all__ = [
    # state + actions
    "create_initial_state",
    "handle_action",
    "resolve_cards",
    "check_win",
    "calculate_scores",
    "advance_turn",
    "seed",
    # config seam
    "GameConfig",
    "build_config",
    "config_for",
    "config_for_version",
    "BASE_GAME",
    "HARBOUR_GAME",
    "BASE_SHARP_GAME",
    "HARBOUR_SHARP_GAME",
    "CONFIGS",
    # card data
    "CARD_DEFS",
    "LANDMARK_DEFS",
]
