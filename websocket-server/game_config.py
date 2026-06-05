"""
Game version configuration (Stage 1 — Engine).

A GameConfig turns a Machi Koro *version* into data: which establishments are in
the supply, which landmarks are required for victory, the starting hand, and
starting coins. The engine code reads everything version-specific from the
active config, so adding a version means adding a config — not changing engine
logic.

Stage 1 slice 1 ships two configs:
  * BASE_GAME    — the standalone base game (15 establishments, 4 landmarks,
                   no City Hall, no Harbor mechanics).
  * HARBOUR_GAME — the full Base + Harbor set the live MVP runs today. This is
                   the default, so existing games and the 45-test
                   characterization harness behave identically.

Sharp (= Millionaire's Row) is a later slice; see
`Developer stages/sprint-2-handoffs/sharp-card-reference.md`.
"""

from dataclasses import dataclass, field
from card_defs import CARD_DEFS, LANDMARK_DEFS


@dataclass(frozen=True)
class GameConfig:
    """Immutable description of a Machi Koro version."""
    name: str
    # Establishment card ids available in this version's supply/market.
    establishment_ids: tuple
    # Landmark ids used this version, in display order. Victory = all built
    # (a pre_built landmark like City Hall is "built" from turn 1).
    landmark_ids: tuple
    # Cards each player starts owning, e.g. {'wheat_field': 1, 'bakery': 1}.
    starting_cards: dict = field(default_factory=lambda: {'wheat_field': 1, 'bakery': 1})
    starting_coins: int = 3

    def __post_init__(self):
        # Fail fast on a malformed config rather than mid-game.
        unknown_cards = [c for c in self.establishment_ids if c not in CARD_DEFS]
        if unknown_cards:
            raise ValueError(f"{self.name}: unknown establishment ids {unknown_cards}")
        known_landmarks = {lm['id'] for lm in LANDMARK_DEFS}
        unknown_lms = [l for l in self.landmark_ids if l not in known_landmarks]
        if unknown_lms:
            raise ValueError(f"{self.name}: unknown landmark ids {unknown_lms}")
        unknown_start = [c for c in self.starting_cards if c not in CARD_DEFS]
        if unknown_start:
            raise ValueError(f"{self.name}: starting card not in CARD_DEFS {unknown_start}")


# ── Base game ────────────────────────────────────────────────────────────────
# 15 establishments (5 blue, 5 green, 2 red, 3 purple) + 4 landmarks.
# No City Hall, no Harbor, no Airport, no Harbor-dependent cards.
BASE_ESTABLISHMENTS = (
    # Blue (Primary)
    'wheat_field', 'ranch', 'forest', 'mine', 'apple_orchard',
    # Green (Secondary)
    'bakery', 'convenience_store', 'cheese_factory', 'furniture_factory', 'farmers_market',
    # Red (Restaurant)
    'cafe', 'family_restaurant',
    # Purple (Major)
    'stadium', 'tv_station', 'business_center',
)
BASE_LANDMARKS = ('train_station', 'shopping_mall', 'amusement_park', 'radio_tower')

BASE_GAME = GameConfig(
    name='Basic',
    establishment_ids=BASE_ESTABLISHMENTS,
    landmark_ids=BASE_LANDMARKS,
)


# ── Harbour (current live default = Base + Harbor expansion) ──────────────────
# All cards/landmarks the engine ships today. Built from the existing defs so
# this stays in lockstep with card_defs.py and preserves current behavior.
HARBOUR_GAME = GameConfig(
    name='Harbour',
    establishment_ids=tuple(CARD_DEFS.keys()),
    landmark_ids=tuple(lm['id'] for lm in LANDMARK_DEFS),
)


CONFIGS = {
    'basic':   BASE_GAME,
    'harbour': HARBOUR_GAME,
}

# Aliases let either the lookup key ('basic') or the config's display name
# ('Basic') resolve to the same config. The table-creation path stores and reads
# the version *key*; a rematch reads the engine's stored config *name*
# (state['version']). Both must land on the same config, so we index by both.
_VERSION_ALIASES = {}
for _key, _cfg in CONFIGS.items():
    _VERSION_ALIASES[_key.lower()] = _cfg
    _VERSION_ALIASES[_cfg.name.lower()] = _cfg


def config_for_version(version):
    """Resolve a stored game_version to its GameConfig, defaulting to Harbour.

    Unknown or missing versions fall back to HARBOUR_GAME — this preserves the
    current live behavior and stays back-compat for tables created before the
    game_version column existed (their value reads as NULL or 'harbour').
    """
    if isinstance(version, str):
        return _VERSION_ALIASES.get(version.strip().lower(), HARBOUR_GAME)
    return HARBOUR_GAME
