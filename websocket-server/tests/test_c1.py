"""Stage 1 slice 2, Phase C1 — Loan Office, Park, Tech Startup.

Three locked defaults (PM brief, 2026-06-06):
  * Park remainder → active player.
  * Tech Startup persists + invest 1/turn.
  * Loan Office negative activation floored at 0.

Deterministic: card math via resolve_cards(state, roll); the build-time payout and
the invest action via handle_action; a few end-to-end checks via the roll handler
with the force_rolls fixture.
"""
import pytest

from game_engine import (
    create_initial_state, resolve_cards, handle_action, advance_turn, card_count,
)
from game_config import BASE_SHARP_GAME, HARBOUR_SHARP_GAME


def P(state, seat):
    return next(p for p in state["players"] if p["seat"] == seat)


def make(config=BASE_SHARP_GAME, num_players=2):
    info = [{"seat": i, "display_name": f"P{i}"} for i in range(num_players)]
    return create_initial_state(info, config=config)


def effect_state(config=BASE_SHARP_GAME, num_players=2):
    """2-player state, hands emptied and coins zeroed. Seat 0 is active."""
    s = make(config, num_players)
    for p in s["players"]:
        p["cards"] = {}
        p["coins"] = 0
    return s


def build_landmark(player, lm_id):
    for lm in player["landmarks"]:
        if lm["id"] == lm_id:
            lm["built"] = True


# ── Loan Office: build payout (+5) and negative activation (−2, floored at 0) ─

class TestLoanOffice:
    def test_build_pays_5_from_bank(self):
        s = make(BASE_SHARP_GAME)
        a = P(s, 0)
        a["coins"] = 3
        s["phase"] = "build"
        s["active_seat"] = 0
        handle_action(s, 0, {"event": "build", "type": "card", "id": "loan_office"})
        assert card_count(P(s, 0), "loan_office") == 1
        assert P(s, 0)["coins"] == 8           # 3 − 0 cost + 5 on build

    def test_activation_pays_2_to_bank(self):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"loan_office": 1}
        a["coins"] = 5
        resolve_cards(s, 5)
        assert a["coins"] == 3

    def test_activation_fires_on_both_5_and_6(self):
        for roll in (5, 6):
            s = effect_state()
            a = P(s, 0)
            a["cards"] = {"loan_office": 1}
            a["coins"] = 4
            resolve_cards(s, roll)
            assert a["coins"] == 2

    def test_floored_at_zero(self):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"loan_office": 1}
        a["coins"] = 1                         # can't pay the full 2
        resolve_cards(s, 6)
        assert a["coins"] == 0                 # floored, never negative

    def test_multi_copy_pays_two_each(self):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"loan_office": 3}
        a["coins"] = 10
        resolve_cards(s, 5)
        assert a["coins"] == 4                 # 3 × 2

    def test_multi_copy_floored(self):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"loan_office": 3}
        a["coins"] = 2                         # owes 6, only has 2
        resolve_cards(s, 5)
        assert a["coins"] == 0

    def test_only_active_player_pays(self):
        # Green: activates on your turn only — an opponent's Loan Office is idle.
        s = effect_state()
        opp = P(s, 1)
        opp["cards"] = {"loan_office": 1}
        opp["coins"] = 5
        resolve_cards(s, 5)
        assert opp["coins"] == 5

    def test_activation_via_roll_handler(self, force_rolls):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"loan_office": 1}
        a["coins"] = 5
        force_rolls(5)                         # single die can land on 5
        handle_action(s, 0, {"event": "roll", "dice_count": 1})
        assert a["coins"] == 3
        assert s["phase"] == "build"


# ── Park: pool & split equally, remainder → active player ────────────────────

class TestPark:
    def test_uneven_split_remainder_to_active(self):
        s = effect_state()
        a, opp = P(s, 0), P(s, 1)
        a["cards"] = {"park": 1}
        a["coins"], opp["coins"] = 5, 2        # total 7 → share 3, remainder 1
        resolve_cards(s, 11)
        assert a["coins"] == 4 and opp["coins"] == 3

    def test_even_split_no_remainder(self):
        s = effect_state()
        a, opp = P(s, 0), P(s, 1)
        a["cards"] = {"park": 1}
        a["coins"], opp["coins"] = 6, 2        # total 8 → 4 each
        resolve_cards(s, 12)
        assert a["coins"] == 4 and opp["coins"] == 4

    def test_three_players_remainder_to_active(self):
        s = effect_state(num_players=3)
        a, b, c = P(s, 0), P(s, 1), P(s, 2)
        a["cards"] = {"park": 1}
        a["coins"], b["coins"], c["coins"] = 5, 3, 2   # total 10 → share 3, rem 1
        resolve_cards(s, 13)
        assert a["coins"] == 4 and b["coins"] == 3 and c["coins"] == 3

    def test_fires_across_11_to_13(self):
        for roll in (11, 12, 13):
            s = effect_state()
            a, opp = P(s, 0), P(s, 1)
            a["cards"] = {"park": 1}
            a["coins"], opp["coins"] = 4, 0
            resolve_cards(s, roll)
            assert a["coins"] == 2 and opp["coins"] == 2

    def test_via_roll_handler(self, force_rolls):
        s = effect_state()
        a, opp = P(s, 0), P(s, 1)
        build_landmark(a, "train_station")     # needed to roll 2 dice
        a["cards"] = {"park": 1}
        a["coins"], opp["coins"] = 5, 2
        force_rolls(5, 6)                       # → 11
        handle_action(s, 0, {"event": "roll", "dice_count": 2})
        assert a["coins"] == 4 and opp["coins"] == 3


# ── Tech Startup: invest (1/turn, persists) + activation (opponents pay total) ─

class TestTechStartup:
    def _ready(self):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"tech_startup": 1}
        s["phase"] = "build"
        return s, a

    def test_invest_moves_one_coin_onto_card(self):
        s, a = self._ready()
        a["coins"] = 2
        out = handle_action(s, 0, {"event": "tech_startup_invest"})
        assert out["broadcast"] is True
        assert a["coins"] == 1
        assert a["investments"]["tech_startup"] == 1
        assert s["tech_invest_used"] is True

    def test_only_once_per_turn(self):
        s, a = self._ready()
        a["coins"] = 5
        handle_action(s, 0, {"event": "tech_startup_invest"})
        out = handle_action(s, 0, {"event": "tech_startup_invest"})
        assert out == {}
        assert a["coins"] == 4 and a["investments"]["tech_startup"] == 1

    def test_invest_resets_and_persists_next_turn(self):
        s, a = self._ready()
        a["coins"] = 5
        handle_action(s, 0, {"event": "tech_startup_invest"})
        advance_turn(s)                         # new turn
        assert s["tech_invest_used"] is False
        assert a["investments"]["tech_startup"] == 1   # persists across turns
        s["phase"] = "build"
        s["active_seat"] = 0
        handle_action(s, 0, {"event": "tech_startup_invest"})
        assert a["investments"]["tech_startup"] == 2   # accumulates

    def test_invest_needs_a_coin(self):
        s, a = self._ready()
        a["coins"] = 0
        assert handle_action(s, 0, {"event": "tech_startup_invest"}) == {}

    def test_invest_needs_ownership(self):
        s, a = self._ready()
        a["cards"] = {}
        a["coins"] = 5
        assert handle_action(s, 0, {"event": "tech_startup_invest"}) == {}

    def test_invest_only_in_build_phase(self):
        s, a = self._ready()
        a["coins"] = 5
        s["phase"] = "roll"
        assert handle_action(s, 0, {"event": "tech_startup_invest"}) == {}

    def test_activation_each_opponent_pays_total_invested(self):
        s = effect_state(num_players=3)
        a, b, c = P(s, 0), P(s, 1), P(s, 2)
        a["cards"] = {"tech_startup": 1}
        a["investments"] = {"tech_startup": 3}
        b["coins"], c["coins"] = 10, 10
        resolve_cards(s, 10)
        assert a["coins"] == 6                  # 3 from each of two opponents
        assert b["coins"] == 7 and c["coins"] == 7
        assert a["investments"]["tech_startup"] == 3   # persists after activation

    def test_activation_clamped_to_opponent_balance(self):
        s = effect_state()
        a, opp = P(s, 0), P(s, 1)
        a["cards"] = {"tech_startup": 1}
        a["investments"] = {"tech_startup": 5}
        opp["coins"] = 2
        resolve_cards(s, 10)
        assert a["coins"] == 2 and opp["coins"] == 0

    def test_activation_with_zero_invested_does_nothing(self):
        s = effect_state()
        a, opp = P(s, 0), P(s, 1)
        a["cards"] = {"tech_startup": 1}
        opp["coins"] = 5
        resolve_cards(s, 10)
        assert a["coins"] == 0 and opp["coins"] == 5

    def test_activation_via_roll_handler(self, force_rolls):
        s = effect_state()
        a, opp = P(s, 0), P(s, 1)
        build_landmark(a, "train_station")
        a["cards"] = {"tech_startup": 1}
        a["investments"] = {"tech_startup": 2}
        opp["coins"] = 9
        force_rolls(4, 6)                        # → 10
        handle_action(s, 0, {"event": "roll", "dice_count": 2})
        assert a["coins"] == 2 and opp["coins"] == 7


# ── State plumbing: new C1 state persists via save/load ──────────────────────

class TestC1StatePersists:
    def test_investments_round_trip(self):
        import json
        s = effect_state()
        P(s, 0)["investments"] = {"tech_startup": 4}
        reloaded = json.loads(json.dumps(s))
        assert P(reloaded, 0)["investments"] == {"tech_startup": 4}
