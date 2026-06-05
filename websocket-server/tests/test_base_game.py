"""Stage 1 (B3) — Base game version tests.

Verifies the Basic GameConfig: the right cards/landmarks are present, no
Harbor content leaks in, the City Hall safety net is correctly absent, and a
Base game can be played to a win. The 45-test characterization suite continues
to guard that Harbour behavior is unchanged.
"""
import pytest

from game_engine import create_initial_state, resolve_cards, check_win
from game_config import (
    BASE_GAME, HARBOUR_GAME, GameConfig, BASE_ESTABLISHMENTS, config_for_version,
)

HARBOR_ONLY_CARDS = {
    'flower_garden', 'mackerel_boat', 'tuna_boat', 'flower_shop', 'food_warehouse',
    'sushi_bar', 'hamburger_stand', 'pizza_joint', 'publisher', 'tax_office',
}
HARBOR_ONLY_LANDMARKS = {'city_hall', 'harbor', 'airport'}


def base_state(num_players=2):
    info = [{"seat": i, "display_name": f"P{i}"} for i in range(num_players)]
    return create_initial_state(info, config=BASE_GAME)


def P(state, seat):
    return next(p for p in state["players"] if p["seat"] == seat)


# ── Composition: only Base content is present ────────────────────────────────

class TestBaseComposition:
    def test_version_label(self):
        assert base_state()["version"] == "Basic"

    def test_supply_is_exactly_the_15_base_cards(self):
        s = base_state()
        assert set(s["supply"]) == set(BASE_ESTABLISHMENTS)
        assert len(BASE_ESTABLISHMENTS) == 15

    def test_no_harbor_cards_in_supply_or_market(self):
        s = base_state()
        assert HARBOR_ONLY_CARDS.isdisjoint(s["supply"])
        market_ids = {c["id"] for c in s["market"]}
        assert HARBOR_ONLY_CARDS.isdisjoint(market_ids)

    def test_four_landmarks_none_built_no_city_hall(self):
        p = P(base_state(), 0)
        lm_ids = {lm["id"] for lm in p["landmarks"]}
        assert lm_ids == {"train_station", "shopping_mall", "amusement_park", "radio_tower"}
        assert HARBOR_ONLY_LANDMARKS.isdisjoint(lm_ids)
        assert all(not lm["built"] for lm in p["landmarks"])

    def test_starting_hand_and_coins(self):
        p = P(base_state(), 0)
        assert p["coins"] == 3
        assert p["cards"] == {"wheat_field": 1, "bakery": 1}

    def test_purple_supply_scales_with_player_count(self):
        s = base_state(num_players=3)
        assert s["supply"]["stadium"] == 3      # purple = one per player
        assert s["supply"]["wheat_field"] == 6  # regular = 6


# ── City Hall safety net is absent in Base, present in Harbour ───────────────

class TestCityHallSafetyNet:
    def test_base_player_at_zero_stays_zero(self):
        # No City Hall in Base: a player who earns nothing keeps 0 coins.
        s = base_state()
        a = P(s, 0)
        a["cards"] = {}
        a["coins"] = 0
        resolve_cards(s, 1)
        assert a["coins"] == 0

    def test_harbour_player_at_zero_gets_one(self):
        # Regression guard for the landmark gate: Harbour pre-builds City Hall,
        # so the safety net still fires.
        info = [{"seat": i, "display_name": f"P{i}"} for i in range(2)]
        s = create_initial_state(info, config=HARBOUR_GAME)
        a = P(s, 0)
        a["cards"] = {}
        a["coins"] = 0
        resolve_cards(s, 1)
        assert a["coins"] == 1


# ── A Base game reaches a winner on its 4 landmarks ──────────────────────────

class TestBaseWinCondition:
    def test_building_all_four_landmarks_wins(self):
        s = base_state()
        a = P(s, 0)
        s["active_seat"] = a["seat"]
        for lm in a["landmarks"]:
            lm["built"] = True
        assert check_win(s) is True
        assert s["winner"] == a["seat"]
        assert s["phase"] == "finished"

    def test_three_of_four_landmarks_does_not_win(self):
        s = base_state()
        a = P(s, 0)
        s["active_seat"] = a["seat"]
        for lm in a["landmarks"][:3]:
            lm["built"] = True
        assert check_win(s) is False
        assert s["winner"] is None


# ── Config validation fails fast ─────────────────────────────────────────────

class TestConfigValidation:
    def test_unknown_establishment_rejected(self):
        with pytest.raises(ValueError):
            GameConfig(name="Bad", establishment_ids=("not_a_card",), landmark_ids=())

    def test_unknown_landmark_rejected(self):
        with pytest.raises(ValueError):
            GameConfig(name="Bad", establishment_ids=(), landmark_ids=("not_a_landmark",))


# ── version → config mapping (B4) ────────────────────────────────────────────
# This is the seam main.py uses at both create_initial_state call sites: a
# table's stored game_version (or a finished game's state['version']) → config.

class TestConfigForVersion:
    def test_basic_key_maps_to_base_game(self):
        assert config_for_version("basic") is BASE_GAME

    def test_harbour_key_maps_to_harbour_game(self):
        assert config_for_version("harbour") is HARBOUR_GAME

    def test_config_name_maps_back_to_same_config(self):
        # Rematch path: state['version'] holds the display name, not the key.
        assert config_for_version("Basic") is BASE_GAME
        assert config_for_version("Harbour") is HARBOUR_GAME

    def test_case_and_whitespace_insensitive(self):
        assert config_for_version("  BASIC ") is BASE_GAME

    def test_unknown_version_falls_back_to_harbour(self):
        assert config_for_version("sharp") is HARBOUR_GAME
        assert config_for_version("nonsense") is HARBOUR_GAME

    def test_missing_version_falls_back_to_harbour(self):
        # None (column absent / NULL) and non-strings must not crash.
        assert config_for_version(None) is HARBOUR_GAME
        assert config_for_version(123) is HARBOUR_GAME

    def test_fallback_produces_current_live_behavior(self):
        # A created game from a missing version is byte-for-byte a Harbour game.
        info = [{"seat": i, "display_name": f"P{i}"} for i in range(2)]
        fell_back = create_initial_state(info, config=config_for_version(None))
        harbour = create_initial_state(info, config=HARBOUR_GAME)
        assert fell_back["version"] == harbour["version"] == "Harbour"
        assert set(fell_back["supply"]) == set(harbour["supply"])
