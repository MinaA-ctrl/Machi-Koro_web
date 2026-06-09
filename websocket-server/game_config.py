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

from dataclasses import dataclass, field, replace
from card_defs import CARD_DEFS, LANDMARK_DEFS, SHARP_CARD_IDS


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
    # Whether the Sharp (Millionaire's Row) add-on is layered on. A config is
    # fully identified by (base, sharp); this flag is the persisted seam Phase D
    # stores alongside game_version. Plain Basic/Harbour leave it False.
    sharp: bool = False
    # Variable Supply (Phase E): only 10 distinct establishment types are face-up
    # at once; selling one out reveals the next from a shuffled deck. Defaults on
    # when Sharp is active (where the larger pool clutters the board), off otherwise.
    variable_supply: bool = False

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
# All non-Sharp cards/landmarks the engine ships today. Derived from the defs so
# it stays in lockstep with card_defs.py and preserves current behavior; the
# Sharp Phase-A cards are excluded so they never leak into plain Harbour — Sharp
# is opt-in only, via build_config(..., sharp=True).
HARBOUR_ESTABLISHMENTS = tuple(cid for cid in CARD_DEFS if cid not in SHARP_CARD_IDS)

HARBOUR_GAME = GameConfig(
    name='Harbour',
    establishment_ids=HARBOUR_ESTABLISHMENTS,
    landmark_ids=tuple(lm['id'] for lm in LANDMARK_DEFS),
)


# ── Sharp (Millionaire's Row) — composable add-on ─────────────────────────────
# Sharp is not a third version: it's a "+ Sharp" flag that layers the Millionaire's
# Row cards onto either base. build_config(base, sharp) is the composition seam —
# Phases B/C add more cards to SHARP_TIER1_IDS, Phase D persists (game_version, sharp).

def build_config(base, sharp=False, variable_supply=None):
    """Compose a GameConfig = `base` (Basic/Harbour) + optional Sharp add-on.

    Sharp appends the Sharp establishment pool to the base's supply and sets the
    `sharp` flag; landmarks, starting hand, and starting coins are the base's
    (Sharp adds no landmarks).

    `variable_supply` defaults on when sharp=True, off otherwise; pass it
    explicitly to override (e.g. variable_supply=False on a Sharp config, or
    =True on a plain base). With sharp=False and no variable-supply override, the
    base is returned unchanged so plain Basic/Harbour keep their identity.
    """
    vs = sharp if variable_supply is None else bool(variable_supply)
    if not sharp:
        if not vs:
            return base                      # unchanged singleton (default-off base)
        return replace(base, variable_supply=True)
    return replace(
        base,
        name=f"{base.name} + Sharp",
        establishment_ids=base.establishment_ids + SHARP_CARD_IDS,
        sharp=True,
        variable_supply=vs,
    )


BASE_SHARP_GAME    = build_config(BASE_GAME, sharp=True)      # "Basic + Sharp"
HARBOUR_SHARP_GAME = build_config(HARBOUR_GAME, sharp=True)   # "Harbour + Sharp"

# Sharp sibling per base, keyed by the base config's name (configs aren't hashable
# — they carry a dict field — so we key by name rather than by the object).
_SHARP_BY_BASE_NAME = {
    BASE_GAME.name.lower():    BASE_SHARP_GAME,
    HARBOUR_GAME.name.lower(): HARBOUR_SHARP_GAME,
}

# Reverse: a composed Sharp singleton's name → its plain base. Lets config_for
# recover the base when a composed name ("Harbour + Sharp") is passed in.
_BASE_OF_SHARP = {
    BASE_SHARP_GAME.name.lower():    BASE_GAME,
    HARBOUR_SHARP_GAME.name.lower(): HARBOUR_GAME,
}


# Version *keys* for the base picker. Sharp is a separate flag, not a key here —
# Phase D persists it as its own column, so CONFIGS stays the two base versions.
CONFIGS = {
    'basic':   BASE_GAME,
    'harbour': HARBOUR_GAME,
}

# Aliases let either the lookup key ('basic') or the config's display name
# ('Basic') resolve to the same config. The table-creation path stores and reads
# the version *key*; a rematch reads the engine's stored config *name*
# (state['version']). Both must land on the same config, so we index by both.
# Composed configs are registered by name too ("Basic + Sharp") so a finished
# Sharp game round-trips on rematch via state['version'].
_VERSION_ALIASES = {}
for _key, _cfg in CONFIGS.items():
    _VERSION_ALIASES[_key.lower()] = _cfg
    _VERSION_ALIASES[_cfg.name.lower()] = _cfg
for _cfg in (BASE_SHARP_GAME, HARBOUR_SHARP_GAME):
    _VERSION_ALIASES[_cfg.name.lower()] = _cfg


def config_for_version(version):
    """Resolve a stored game_version (or config name) to its GameConfig.

    Defaults to HARBOUR_GAME for unknown/missing values — this preserves current
    live behavior and stays back-compat for tables created before the game_version
    column existed (NULL or 'harbour'). Recognizes composed names ("Basic + Sharp")
    so a Sharp game's state['version'] round-trips on rematch.
    """
    if isinstance(version, str):
        return _VERSION_ALIASES.get(version.strip().lower(), HARBOUR_GAME)
    return HARBOUR_GAME


def config_for(base, sharp=False, variable_supply=None):
    """Resolve (base, sharp, variable_supply) to a GameConfig.

    The seam main.py persists against: it stores (game_version, sharp,
    variable_supply) and resolves here. The three are independent — `base` is a
    version key/name ('basic'/'harbour' or 'Basic'/'Harbour'); `sharp` layers the
    add-on; `variable_supply` is the supply mode.

    `variable_supply=None` keeps build_config's default (on for Sharp, off
    otherwise); pass True/False to override it explicitly (the host's choice).
    Canonical (base, sharp) combos in their default supply mode return the shared
    singletons, so existing round-trips still compare equal by identity.
    """
    base_cfg = config_for_version(base)
    if base_cfg.sharp:                       # a composed name resolved — recover its base
        base_cfg = _BASE_OF_SHARP.get(base_cfg.name.lower(), base_cfg)
    canonical = (_SHARP_BY_BASE_NAME.get(base_cfg.name.lower(), base_cfg)
                 if sharp else base_cfg)
    if variable_supply is None or bool(variable_supply) == canonical.variable_supply:
        return canonical
    return build_config(base_cfg, sharp=bool(sharp), variable_supply=bool(variable_supply))
