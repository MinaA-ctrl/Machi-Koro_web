"""Stage 1 slice 2, Phase B — Renovation mechanic + Winery & Cleaning Company.

Renovation model (documented in sprint-2-handoffs/sharp-composition-seam.md):
a card carries a *closed-copy count* per (player, card_id) in
player['renovation']. A closed copy skips exactly one activation: when the card's
number comes up the closed copies reopen and pay nothing that time; only the open
(owned − closed) copies pay. Counts, not identities, so multiple copies renovate
independently — matching the physical per-card tokens.

All deterministic: card math via resolve_cards(state, roll); the interactive
Cleaning Company path via _set_interactive_phase + the cleaning_company_pick
handle_action event (the Phase-D frontend will drive the same seam).
"""
import json
import pytest

from game_engine import (
    create_initial_state, resolve_cards, handle_action,
    _set_interactive_phase, _cleaning_targets,
    closed_copies, active_copies,
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


# ── State plumbing ───────────────────────────────────────────────────────────

class TestRenovationState:
    def test_fresh_state_has_empty_renovation(self):
        for p in make()["players"]:
            assert p["renovation"] == {}

    def test_renovation_survives_json_round_trip(self):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"bakery": 2}
        a["renovation"] = {"bakery": 1}
        reloaded = json.loads(json.dumps(s))   # mirrors the per-action save/load
        assert P(reloaded, 0)["renovation"] == {"bakery": 1}
        # …and the reloaded state resolves with the renovation honored.
        resolve_cards(reloaded, 2)             # 1 closed bakery reopens, 1 pays
        assert P(reloaded, 0)["coins"] == 1
        assert P(reloaded, 0)["renovation"] == {}


# ── The generic skip-then-reopen rule (any card type) ────────────────────────

class TestSkipThenReopen:
    def test_closed_copy_skips_one_activation_then_reopens(self):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"bakery": 1}
        a["renovation"] = {"bakery": 1}     # the single copy is closed
        resolve_cards(s, 2)                 # its number comes up: reopen, pay 0
        assert a["coins"] == 0
        assert closed_copies(a, "bakery") == 0
        resolve_cards(s, 2)                 # now open: pays normally
        assert a["coins"] == 1

    def test_partial_close_only_open_copies_pay(self):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"bakery": 3}
        a["renovation"] = {"bakery": 1}     # 2 open, 1 closed
        resolve_cards(s, 2)                 # 2 pay, 1 reopens (pays 0)
        assert a["coins"] == 2
        assert closed_copies(a, "bakery") == 0


# ── Winery: payout then self-close ───────────────────────────────────────────

class TestWinery:
    def test_pays_6_per_vineyard_then_closes(self):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"winery": 1, "vineyard": 2}
        resolve_cards(s, 9)
        assert a["coins"] == 12                  # 1 copy × 6 × 2 vineyards
        assert closed_copies(a, "winery") == 1   # closed for renovation

    def test_next_matching_roll_reopens_and_pays_zero(self):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"winery": 1, "vineyard": 2}
        resolve_cards(s, 9)                       # pays 12, closes
        resolve_cards(s, 9)                       # reopens, pays 0
        assert a["coins"] == 12
        assert closed_copies(a, "winery") == 0
        resolve_cards(s, 9)                       # open again → pays again
        assert a["coins"] == 24

    def test_zero_vineyards_pays_nothing_but_still_closes(self):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"winery": 1}
        resolve_cards(s, 9)
        assert a["coins"] == 0
        assert closed_copies(a, "winery") == 1   # closes even when it paid 0

    def test_multi_copy_all_close_together(self):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"winery": 3, "vineyard": 1}
        resolve_cards(s, 9)
        assert a["coins"] == 18                   # 3 × 6 × 1
        assert closed_copies(a, "winery") == 3
        resolve_cards(s, 9)                        # all reopen, pay 0
        assert a["coins"] == 18 and closed_copies(a, "winery") == 0
        resolve_cards(s, 9)
        assert a["coins"] == 36

    def test_multi_copy_independent_when_mixed(self):
        # Per-copy model: 2 owned, 1 already closed. The open one pays and closes;
        # the closed one reopens — so exactly 1 stays closed afterward.
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"winery": 2, "vineyard": 1}
        a["renovation"] = {"winery": 1}
        resolve_cards(s, 9)
        assert a["coins"] == 6                     # only the 1 open copy paid
        assert closed_copies(a, "winery") == 1


# ── Renovated cards still count for other cards' "count" effects ─────────────
# PM ruling (2026-06-06): a renovated card is still owned ("in hand, just doesn't
# function"), so it still counts toward other cards' totals.

class TestRenovatedCardsStillCount:
    def test_winery_counts_renovated_vineyard(self):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"winery": 1, "vineyard": 2}
        a["renovation"] = {"vineyard": 2}        # both Vineyards closed
        resolve_cards(s, 9)                       # Vineyard's number (7) isn't up
        assert a["coins"] == 12                   # still 6 × 2 owned Vineyards
        assert closed_copies(a, "vineyard") == 2  # they stay closed

    def test_soda_counts_renovated_red(self):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"soda_bottling_plant": 1, "cafe": 1}
        a["renovation"] = {"cafe": 1}             # the Red is closed
        resolve_cards(s, 11)                      # Café's number (3) isn't up
        assert a["coins"] == 1                    # still counts the owned (closed) Red


# ── Cleaning Company: interactive close-all-of-type ──────────────────────────

class TestCleaningCompany:
    def _armed(self, config=BASE_SHARP_GAME):
        """Active (seat 0) holds Cleaning Company; last_roll=8 (its number)."""
        s = effect_state(config)
        s["last_roll"] = 8
        P(s, 0)["cards"] = {"cleaning_company": 1}
        return s

    def test_phase_and_prompt_list_valid_targets(self):
        s = self._armed()
        P(s, 0)["cards"]["cafe"] = 1
        P(s, 1)["cards"] = {"cafe": 2, "wheat_field": 1}
        _set_interactive_phase(s, 8)
        assert s["phase"] == "cleaning_company"
        targets = s["pending_prompt"]["targets"]
        assert "cafe" in targets and "wheat_field" in targets
        assert "cleaning_company" not in targets        # Majors excluded

    def test_closes_all_copies_of_type_and_collects_one_each(self):
        s = self._armed()
        P(s, 0)["cards"]["cafe"] = 1
        P(s, 1)["cards"] = {"cafe": 2}
        _set_interactive_phase(s, 8)
        out = handle_action(s, 0, {"event": "cleaning_company_pick", "card_type": "cafe"})
        assert out["broadcast"] is True
        assert closed_copies(P(s, 0), "cafe") == 1
        assert closed_copies(P(s, 1), "cafe") == 2
        assert P(s, 0)["coins"] == 3                    # 1 coin per copy closed (1+2)
        assert s["phase"] == "build"                    # flows on after the pick

    def test_rejects_major_target(self):
        s = self._armed()
        P(s, 0)["cards"]["stadium"] = 1
        s["phase"] = "cleaning_company"
        s["pending_prompt"] = {"type": "cleaning_company", "targets": ["stadium"]}
        out = handle_action(s, 0, {"event": "cleaning_company_pick", "card_type": "stadium"})
        assert out == {}                               # server-side rejection
        assert closed_copies(P(s, 0), "stadium") == 0
        assert s["phase"] == "cleaning_company"        # still waiting on a valid pick

    def test_rejects_absent_type(self):
        s = self._armed()
        s["phase"] = "cleaning_company"
        s["pending_prompt"] = {"type": "cleaning_company", "targets": []}
        out = handle_action(s, 0, {"event": "cleaning_company_pick", "card_type": "forest"})
        assert out == {}
        assert P(s, 0)["coins"] == 0

    def test_closed_target_skips_one_activation_then_reopens(self):
        # Cleaning closes the opponent's Cafés; the next roll-3 they reopen and
        # take nothing, the one after that they take normally.
        s = self._armed()
        opp = P(s, 1)
        opp["cards"] = {"cafe": 2}
        _set_interactive_phase(s, 8)
        handle_action(s, 0, {"event": "cleaning_company_pick", "card_type": "cafe"})
        assert closed_copies(opp, "cafe") == 2

        active = P(s, 0)
        assert active["coins"] == 2                    # collector got 1 per closed copy (2)
        active["coins"] = 10                           # reset to isolate the red transfer below
        resolve_cards(s, 3)                            # cafés reopen, take 0
        assert active["coins"] == 10 and opp["coins"] == 0
        assert closed_copies(opp, "cafe") == 0
        resolve_cards(s, 3)                            # now open: opp takes 2
        assert active["coins"] == 8 and opp["coins"] == 2

    def test_fully_closed_type_is_not_a_target(self):
        s = self._armed()
        opp = P(s, 1)
        opp["cards"] = {"cafe": 2}
        opp["renovation"] = {"cafe": 2}               # already fully renovated
        assert "cafe" not in _cleaning_targets(s)


def build_landmark(player, lm_id):
    for lm in player["landmarks"]:
        if lm["id"] == lm_id:
            lm["built"] = True


# ── End-to-end through the real roll handler (the path main.py drives) ────────
# Train Station lets the active player roll 2 dice, so we can script totals of
# 8 (Cleaning Company) and 9 (Winery) via the force_rolls fixture.

class TestRollPathIntegration:
    def test_winery_via_roll(self, force_rolls):
        s = effect_state()
        a = P(s, 0)
        build_landmark(a, "train_station")
        a["cards"] = {"winery": 1, "vineyard": 2}
        force_rolls(4, 5)                              # → 9
        handle_action(s, 0, {"event": "roll", "dice_count": 2})
        assert a["coins"] == 12
        assert closed_copies(a, "winery") == 1
        assert s["phase"] == "build"

    def test_cleaning_via_roll_enters_phase_then_resolves(self, force_rolls):
        s = effect_state()
        a, opp = P(s, 0), P(s, 1)
        build_landmark(a, "train_station")
        a["cards"] = {"cleaning_company": 1}
        opp["cards"] = {"cafe": 2}
        force_rolls(3, 5)                              # → 8 (not doubles)
        handle_action(s, 0, {"event": "roll", "dice_count": 2})
        assert s["phase"] == "cleaning_company"
        assert "cafe" in s["pending_prompt"]["targets"]
        handle_action(s, 0, {"event": "cleaning_company_pick", "card_type": "cafe"})
        assert closed_copies(opp, "cafe") == 2
        assert a["coins"] == 2
        assert s["phase"] == "build"


# ── Cross-base sanity: renovation is base-agnostic ───────────────────────────

class TestRenovationCrossBase:
    def test_winery_cycle_on_harbour(self):
        s = effect_state(HARBOUR_SHARP_GAME)
        a = P(s, 0)
        a["cards"] = {"winery": 1, "vineyard": 1}
        a["coins"] = 5                                 # keep >0 so City Hall can't muddy it
        resolve_cards(s, 9)
        assert a["coins"] == 11 and closed_copies(a, "winery") == 1
