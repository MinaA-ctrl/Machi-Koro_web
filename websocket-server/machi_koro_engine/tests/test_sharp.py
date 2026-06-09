"""Stage 1 slice 2, Phase A — Sharp (Millionaire's Row) add-on.

Sharp is a composable add-on, not a third version: a "+ Sharp" flag that layers
the Millionaire's Row cards onto either Basic or Harbour. Phase A ships config
composition, the 6 Tier-1 cards, and the landmarks_built helper.

These tests cover:
  * composition across all 4 combos (no Sharp leakage into plain bases),
  * the round-trip seam used by rematch (config name → config) and the
    (base, sharp) resolver Phase D will persist against,
  * each Tier-1 card incl. both sides of every conditional,
  * the landmarks_built helper on both bases (City Hall excluded).

Everything is deterministic: card math goes through resolve_cards(state, roll)
directly, no dice. The existing 64-test suite continues to guard Basic/Harbour.
"""
import pytest

from machi_koro_engine.game_engine import create_initial_state, resolve_cards, landmarks_built
from machi_koro_engine.game_config import (
    BASE_GAME, HARBOUR_GAME, BASE_SHARP_GAME, HARBOUR_SHARP_GAME,
    build_config, config_for, config_for_version,
    BASE_ESTABLISHMENTS, HARBOUR_ESTABLISHMENTS,
)
from machi_koro_engine.card_defs import SHARP_TIER1_IDS, SHARP_CARD_IDS


def P(state, seat):
    return next(p for p in state["players"] if p["seat"] == seat)


def make(config, num_players=2):
    info = [{"seat": i, "display_name": f"P{i}"} for i in range(num_players)]
    return create_initial_state(info, config=config)


def effect_state(config=BASE_SHARP_GAME, num_players=2):
    """A 2-player state with every hand emptied and coins zeroed, so a single
    resolve_cards call exercises exactly the cards a test assigns. Seat 0 is the
    active (rolling) player; seat 1 is the opponent."""
    s = make(config, num_players)
    for p in s["players"]:
        p["cards"] = {}
        p["coins"] = 0
    return s


def set_landmarks(player, n):
    """Mark the player's first n non-City-Hall landmarks built, the rest unbuilt."""
    built = 0
    for lm in player["landmarks"]:
        if lm["id"] == "city_hall":
            continue
        lm["built"] = built < n
        if built < n:
            built += 1
    assert built == n, "test asked for more landmarks than this base has"


# ── 1. Config composition across the 4 combos ────────────────────────────────

class TestComposition:
    def test_establishment_counts(self):
        # Full Sharp pool: all 13 (6 Tier-1 + 2 Phase-B + 3 Phase-C1 + 2 Phase-C2).
        assert len(SHARP_CARD_IDS) == 13
        assert len(BASE_GAME.establishment_ids) == 15
        assert len(HARBOUR_GAME.establishment_ids) == 25
        assert len(BASE_SHARP_GAME.establishment_ids) == 15 + 13
        assert len(HARBOUR_SHARP_GAME.establishment_ids) == 25 + 13

    def test_sharp_cards_present_only_when_sharp(self):
        sharp_set = set(SHARP_CARD_IDS)
        assert set(SHARP_TIER1_IDS) <= sharp_set            # Tier-1 still included
        assert {"winery", "cleaning_company"} <= sharp_set  # Phase B
        assert {"loan_office", "park", "tech_startup"} <= sharp_set        # Phase C1
        assert {"demolition_company", "moving_company"} <= sharp_set       # Phase C2
        # Present in the composed configs…
        assert sharp_set <= set(BASE_SHARP_GAME.establishment_ids)
        assert sharp_set <= set(HARBOUR_SHARP_GAME.establishment_ids)
        # …and absent from the plain bases (no leakage).
        assert sharp_set.isdisjoint(BASE_GAME.establishment_ids)
        assert sharp_set.isdisjoint(HARBOUR_GAME.establishment_ids)

    def test_composed_is_base_plus_sharp_exactly(self):
        assert set(BASE_SHARP_GAME.establishment_ids) == set(BASE_ESTABLISHMENTS) | set(SHARP_CARD_IDS)
        assert set(HARBOUR_SHARP_GAME.establishment_ids) == set(HARBOUR_ESTABLISHMENTS) | set(SHARP_CARD_IDS)

    def test_landmarks_unchanged_by_sharp(self):
        # Sharp adds no landmarks — each composed config keeps its base's set.
        assert BASE_SHARP_GAME.landmark_ids == BASE_GAME.landmark_ids
        assert HARBOUR_SHARP_GAME.landmark_ids == HARBOUR_GAME.landmark_ids
        assert len(BASE_SHARP_GAME.landmark_ids) == 4       # 4 buildable
        assert len(HARBOUR_SHARP_GAME.landmark_ids) == 7    # City Hall + 6 buildable

    def test_starting_hand_and_coins_inherited(self):
        for cfg in (BASE_SHARP_GAME, HARBOUR_SHARP_GAME):
            assert cfg.starting_cards == {"wheat_field": 1, "bakery": 1}
            assert cfg.starting_coins == 3

    def test_sharp_flag(self):
        assert BASE_GAME.sharp is False and HARBOUR_GAME.sharp is False
        assert BASE_SHARP_GAME.sharp is True and HARBOUR_SHARP_GAME.sharp is True

    def test_build_config_without_sharp_returns_base_unchanged(self):
        assert build_config(BASE_GAME, sharp=False) is BASE_GAME
        assert build_config(HARBOUR_GAME, sharp=False) is HARBOUR_GAME

    def test_created_state_supply_and_market(self):
        # Verify the composed *pool* (all 13 Sharp types at full counts). Sharp now
        # defaults to Variable Supply (only 10 face-up), so pin it off here to see
        # the whole classic supply; Variable Supply has its own test module.
        s = make(build_config(BASE_GAME, sharp=True, variable_supply=False), num_players=2)
        assert s["version"] == "Basic + Sharp"
        for cid in SHARP_TIER1_IDS + ("winery", "loan_office",
                                      "demolition_company", "moving_company"):
            assert s["supply"][cid] == 6                 # regular cards
        for cid in ("cleaning_company", "park", "tech_startup"):
            assert s["supply"][cid] == 2                 # Purple Major → per-player
        market_ids = {c["id"] for c in s["market"]}
        assert set(SHARP_CARD_IDS) <= market_ids
        # plain Basic still excludes the whole Sharp pool
        assert set(SHARP_CARD_IDS).isdisjoint(make(BASE_GAME)["supply"])


# ── 2. Round-trip / rematch seam ─────────────────────────────────────────────

class TestRoundTrip:
    def test_name_round_trips_via_config_for_version(self):
        # Rematch path: state['version'] holds the display name.
        assert config_for_version("Basic + Sharp") is BASE_SHARP_GAME
        assert config_for_version("Harbour + Sharp") is HARBOUR_SHARP_GAME

    def test_name_round_trip_is_case_and_space_insensitive(self):
        assert config_for_version("  harbour + sharp ") is HARBOUR_SHARP_GAME

    def test_config_for_base_and_flag(self):
        # Phase D persists (game_version, sharp) and resolves via this seam.
        assert config_for("basic", True) is BASE_SHARP_GAME
        assert config_for("harbour", True) is HARBOUR_SHARP_GAME
        assert config_for("basic", False) is BASE_GAME
        assert config_for("harbour", False) is HARBOUR_GAME

    def test_config_for_normalizes_base_name(self):
        assert config_for("Harbour", True) is HARBOUR_SHARP_GAME

    def test_plain_versions_unaffected(self):
        # No Sharp leakage into the existing resolver.
        assert config_for_version("basic") is BASE_GAME
        assert config_for_version("harbour") is HARBOUR_GAME
        assert config_for_version("sharp") is HARBOUR_GAME  # unknown → fallback

    def test_full_rematch_round_trip(self):
        # A finished Sharp game's stored label rebuilds the same composed config.
        finished = make(HARBOUR_SHARP_GAME)
        rebuilt = create_initial_state(
            [{"seat": i, "display_name": f"P{i}"} for i in range(2)],
            config=config_for_version(finished["version"]),
        )
        assert rebuilt["version"] == "Harbour + Sharp"
        # Same composed config resolves on rematch. Variable Supply randomizes which
        # 10 are face-up per game, so compare the full card pool (face-up + deck).
        pool = lambda s: set(s["supply"]) | set(s.get("deck", []))
        assert pool(rebuilt) == pool(finished)


# ── 3. landmarks_built helper ────────────────────────────────────────────────

class TestLandmarksBuilt:
    def test_basic_counts_built_only(self):
        p = P(make(BASE_GAME), 0)
        assert landmarks_built(p) == 0
        set_landmarks(p, 2)
        assert landmarks_built(p) == 2

    def test_harbour_excludes_city_hall(self):
        # Harbour pre-builds City Hall; it must not count.
        p = P(make(HARBOUR_GAME), 0)
        assert any(lm["id"] == "city_hall" and lm["built"] for lm in p["landmarks"])
        assert landmarks_built(p) == 0
        set_landmarks(p, 3)
        assert landmarks_built(p) == 3  # still excludes the pre-built City Hall


# ── 4. The 6 Tier-1 cards, both sides of every condition ─────────────────────

class TestVineyard:
    def test_pays_3_flat_on_anyones_turn(self):
        s = effect_state()
        owner = P(s, 1)  # opponent — blue activates regardless of whose turn
        owner["cards"] = {"vineyard": 1}
        resolve_cards(s, 7)
        assert owner["coins"] == 3

    def test_per_copy_and_unconditional(self):
        s = effect_state()
        owner = P(s, 1)
        owner["cards"] = {"vineyard": 2}
        set_landmarks(owner, 3)  # no landmark condition — pays anyway
        resolve_cards(s, 7)
        assert owner["coins"] == 6


class TestCornField:
    def test_pays_when_owner_has_one_or_fewer_landmarks(self):
        s = effect_state()
        owner = P(s, 1)
        owner["cards"] = {"corn_field": 1}
        set_landmarks(owner, 1)
        resolve_cards(s, 3)
        assert owner["coins"] == 1

    def test_silent_when_owner_has_two_or_more_landmarks(self):
        s = effect_state()
        owner = P(s, 1)
        owner["cards"] = {"corn_field": 1}
        set_landmarks(owner, 2)
        resolve_cards(s, 4)
        assert owner["coins"] == 0

    def test_per_copy(self):
        s = effect_state()
        owner = P(s, 1)
        owner["cards"] = {"corn_field": 3}
        set_landmarks(owner, 0)
        resolve_cards(s, 3)
        assert owner["coins"] == 3


class TestGeneralStore:
    def test_pays_active_when_one_or_fewer_landmarks(self):
        s = effect_state()
        active = P(s, 0)
        active["cards"] = {"general_store": 1}
        set_landmarks(active, 1)
        resolve_cards(s, 2)
        assert active["coins"] == 2

    def test_silent_when_active_has_two_or_more(self):
        s = effect_state()
        active = P(s, 0)
        active["cards"] = {"general_store": 1}
        set_landmarks(active, 2)
        resolve_cards(s, 2)
        assert active["coins"] == 0

    def test_only_active_player_collects(self):
        # Green is your-turn-only: an opponent's General Store pays nothing.
        s = effect_state()
        opp = P(s, 1)
        opp["cards"] = {"general_store": 1}
        set_landmarks(opp, 0)
        resolve_cards(s, 2)
        assert opp["coins"] == 0


class TestSodaBottlingPlant:
    def test_counts_red_across_all_players_including_owner(self):
        s = effect_state()
        active = P(s, 0)
        opp = P(s, 1)
        active["cards"] = {"soda_bottling_plant": 1, "cafe": 1}  # own red counts too
        opp["cards"] = {"family_restaurant": 2}                  # opponents' reds count
        resolve_cards(s, 11)
        assert active["coins"] == 3  # 1 + 2 red establishments

    def test_zero_when_no_red_anywhere(self):
        s = effect_state()
        active = P(s, 0)
        active["cards"] = {"soda_bottling_plant": 1}
        resolve_cards(s, 11)
        assert active["coins"] == 0

    def test_per_copy(self):
        s = effect_state()
        active = P(s, 0)
        opp = P(s, 1)
        active["cards"] = {"soda_bottling_plant": 2}
        opp["cards"] = {"cafe": 3}
        resolve_cards(s, 11)
        assert active["coins"] == 6  # 2 copies × 3 reds


class TestFrenchRestaurant:
    def test_takes_5_when_roller_has_two_or_more_landmarks(self):
        s = effect_state()
        active = P(s, 0)
        owner = P(s, 1)  # opponent — red activates on the active player's turn
        active["coins"] = 8
        owner["cards"] = {"french_restaurant": 1}
        set_landmarks(active, 2)
        resolve_cards(s, 5)
        assert active["coins"] == 3 and owner["coins"] == 5

    def test_silent_when_roller_has_one_or_fewer(self):
        s = effect_state()
        active = P(s, 0)
        owner = P(s, 1)
        active["coins"] = 8
        owner["cards"] = {"french_restaurant": 1}
        set_landmarks(active, 1)
        resolve_cards(s, 5)
        assert active["coins"] == 8 and owner["coins"] == 0

    def test_per_copy_capped_by_active_balance(self):
        s = effect_state()
        active = P(s, 0)
        owner = P(s, 1)
        active["coins"] = 7          # less than 2 copies × 5 = 10
        owner["cards"] = {"french_restaurant": 2}
        set_landmarks(active, 2)
        resolve_cards(s, 5)
        assert active["coins"] == 0 and owner["coins"] == 7  # capped at what's there

    def test_works_on_harbour_base(self):
        # Cross-base: conditional counts constructed landmarks regardless of base.
        s = effect_state(config=HARBOUR_SHARP_GAME)
        active = P(s, 0)
        owner = P(s, 1)
        active["coins"] = 9          # stays >0 so City Hall safety net can't muddy it
        owner["cards"] = {"french_restaurant": 1}
        set_landmarks(active, 2)
        resolve_cards(s, 5)
        assert active["coins"] == 4 and owner["coins"] == 5


class TestPrivateClub:
    def test_takes_all_when_roller_has_three_or_more_landmarks(self):
        s = effect_state()
        active = P(s, 0)
        owner = P(s, 1)
        active["coins"] = 17
        owner["cards"] = {"private_club": 1}
        set_landmarks(active, 3)
        resolve_cards(s, 12)
        assert active["coins"] == 0 and owner["coins"] == 17

    def test_silent_when_roller_has_two_or_fewer(self):
        s = effect_state()
        active = P(s, 0)
        owner = P(s, 1)
        active["coins"] = 17
        owner["cards"] = {"private_club": 1}
        set_landmarks(active, 2)
        resolve_cards(s, 13)
        assert active["coins"] == 17 and owner["coins"] == 0

    def test_extra_copies_redundant_still_takes_all_once(self):
        s = effect_state()
        active = P(s, 0)
        owner = P(s, 1)
        active["coins"] = 17
        owner["cards"] = {"private_club": 2}
        set_landmarks(active, 4)
        resolve_cards(s, 14)
        assert active["coins"] == 0 and owner["coins"] == 17  # all, not doubled
