"""Stage 1 slice 2, Phase C2 — Demolition Company & Moving Company (the finale).

Both are interactive (engine handlers; frontend prompts are Phase D). Demolition
breaks the "landmarks only increase" invariant — a built landmark goes unbuilt —
so the invariant cases (not-a-winner, rebuild, no-op) are tested explicitly.

Determinism: most tests use `fire(state, roll)` = resolve_cards + the real
_set_interactive_phase (so the renovation stash is set exactly as in play), then
drive the pick handlers; a couple go end-to-end through the roll handler with
force_rolls. After this, all 13 Sharp cards exist.
"""
import pytest

from game_engine import (
    create_initial_state, resolve_cards, handle_action, _set_interactive_phase,
    check_win, card_count, has_landmark, closed_copies,
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


def set_built(player, ids):
    for lm in player["landmarks"]:
        if lm["id"] in ids:
            lm["built"] = True


def fire(state, roll):
    """Mimic _finish_roll without dice: resolve the roll (sets the renovation
    stash) then enter the interactive phase chain."""
    state["last_roll"] = roll
    resolve_cards(state, roll)
    _set_interactive_phase(state, roll)


# ── Demolition Company ───────────────────────────────────────────────────────

class TestDemolition:
    def test_demolish_chosen_landmark_pays_8(self):
        s = effect_state()
        a = P(s, 0)
        set_built(a, ["train_station", "shopping_mall"])   # 2 demolishable → prompt
        a["cards"] = {"demolition_company": 1}
        fire(s, 4)
        assert s["phase"] == "demolition"
        assert set(s["pending_prompt"]["targets"]) == {"train_station", "shopping_mall"}
        handle_action(s, 0, {"event": "demolition_pick", "landmark_id": "train_station"})
        assert not has_landmark(a, "train_station")
        assert has_landmark(a, "shopping_mall")
        assert a["coins"] == 8
        assert s["phase"] == "build"

    def test_single_demolishable_auto_resolves(self):
        s = effect_state()
        a = P(s, 0)
        set_built(a, ["radio_tower"])                      # only one choice
        a["cards"] = {"demolition_company": 1}
        fire(s, 4)
        assert not has_landmark(a, "radio_tower")
        assert a["coins"] == 8
        assert s["phase"] == "build"                       # no prompt was needed

    def test_no_demolishable_landmark_does_nothing(self):
        # Harbour: only City Hall is built, and it can never be demolished.
        s = effect_state(HARBOUR_SHARP_GAME)
        a = P(s, 0)
        a["coins"] = 5                                     # >0 so City Hall net stays out
        a["cards"] = {"demolition_company": 1}
        fire(s, 4)
        assert s["phase"] == "build"
        assert a["coins"] == 5                             # no +8
        assert has_landmark(a, "city_hall")

    def test_city_hall_can_never_be_demolished(self):
        s = effect_state(HARBOUR_SHARP_GAME)
        a = P(s, 0)
        a["coins"] = 5
        set_built(a, ["harbor", "train_station"])          # 2 demolishable (not City Hall)
        a["cards"] = {"demolition_company": 1}
        fire(s, 4)
        assert s["phase"] == "demolition"
        assert "city_hall" not in s["pending_prompt"]["targets"]
        assert handle_action(s, 0, {"event": "demolition_pick", "landmark_id": "city_hall"}) == {}
        assert has_landmark(a, "city_hall")
        # a valid pick still works
        handle_action(s, 0, {"event": "demolition_pick", "landmark_id": "harbor"})
        assert not has_landmark(a, "harbor")
        assert a["coins"] == 13

    def test_demolisher_is_not_a_winner_game_continues(self):
        # All four landmarks built, then one demolished → not a win.
        s = effect_state()
        a = P(s, 0)
        for lm in a["landmarks"]:
            lm["built"] = True
        a["cards"] = {"demolition_company": 1}
        fire(s, 4)
        handle_action(s, 0, {"event": "demolition_pick", "landmark_id": "train_station"})
        assert check_win(s) is False
        assert s["winner"] is None
        assert s["phase"] != "finished"

    def test_demolished_landmark_can_be_rebuilt_and_win(self):
        s = effect_state()
        a = P(s, 0)
        for lm in a["landmarks"]:
            lm["built"] = True
        a["cards"] = {"demolition_company": 1}
        fire(s, 4)
        handle_action(s, 0, {"event": "demolition_pick", "landmark_id": "train_station"})
        assert not has_landmark(a, "train_station")
        a["coins"] = 100                                   # enough to rebuild
        handle_action(s, 0, {"event": "build", "type": "landmark", "id": "train_station"})
        assert has_landmark(a, "train_station")            # rebuilt via the normal path
        assert s["winner"] == 0                            # all four built again → win

    def test_multi_copy_demolishes_up_to_n(self):
        s = effect_state()
        a = P(s, 0)
        set_built(a, ["train_station", "shopping_mall", "radio_tower"])  # 3 demolishable
        a["cards"] = {"demolition_company": 2}             # demolish 2
        fire(s, 4)
        handle_action(s, 0, {"event": "demolition_pick", "landmark_id": "train_station"})
        assert s["phase"] == "demolition"                 # one demolition left → re-prompt
        handle_action(s, 0, {"event": "demolition_pick", "landmark_id": "shopping_mall"})
        assert s["phase"] == "build"
        built = [lm["id"] for lm in a["landmarks"] if lm["built"]]
        assert built == ["radio_tower"]
        assert a["coins"] == 16                            # 8 per actual demolition

    def test_multi_copy_capped_by_available(self):
        s = effect_state()
        a = P(s, 0)
        set_built(a, ["amusement_park"])                  # only 1 demolishable
        a["cards"] = {"demolition_company": 3}            # 3 copies, but only 1 to take
        fire(s, 4)
        assert a["coins"] == 8                            # paid only for the one actual
        assert not has_landmark(a, "amusement_park")

    def test_renovation_skips_one_activation(self):
        s = effect_state()
        a = P(s, 0)
        set_built(a, ["train_station"])
        a["cards"] = {"demolition_company": 1}
        a["renovation"] = {"demolition_company": 1}        # the copy is closed
        fire(s, 4)                                         # reopens, fires 0 this roll
        assert has_landmark(a, "train_station") and a["coins"] == 0
        assert closed_copies(a, "demolition_company") == 0
        fire(s, 4)                                         # now open → demolishes
        assert not has_landmark(a, "train_station") and a["coins"] == 8

    def test_via_roll_handler(self, force_rolls):
        s = effect_state()
        a = P(s, 0)
        set_built(a, ["train_station"])
        a["cards"] = {"demolition_company": 1}
        force_rolls(4)                                     # single die → 4
        handle_action(s, 0, {"event": "roll", "dice_count": 1})
        assert not has_landmark(a, "train_station")
        assert a["coins"] == 8 and s["phase"] == "build"


# ── Moving Company ───────────────────────────────────────────────────────────

class TestMovingCompany:
    def test_give_non_major_card_for_4(self):
        s = effect_state()
        a, opp = P(s, 0), P(s, 1)
        a["cards"] = {"moving_company": 1, "cafe": 1}
        fire(s, 9)
        assert s["phase"] == "moving_company"
        pp = s["pending_prompt"]
        assert "cafe" in pp["giveable"] and "moving_company" in pp["giveable"]
        assert pp["targets"] == [1]
        handle_action(s, 0, {"event": "moving_company_pick", "card_id": "cafe", "target_seat": 1})
        assert card_count(a, "cafe") == 0 and card_count(opp, "cafe") == 1
        assert a["coins"] == 4
        assert s["phase"] == "build"

    def test_fires_on_9_and_10(self):
        for roll in (9, 10):
            s = effect_state()
            P(s, 0)["cards"] = {"moving_company": 1, "cafe": 1}
            fire(s, roll)
            assert s["phase"] == "moving_company"

    def test_can_give_moving_company_itself(self):
        s = effect_state()
        a, opp = P(s, 0), P(s, 1)
        a["cards"] = {"moving_company": 1}                 # its only card
        fire(s, 9)
        handle_action(s, 0, {"event": "moving_company_pick",
                             "card_id": "moving_company", "target_seat": 1})
        assert card_count(a, "moving_company") == 0
        assert card_count(opp, "moving_company") == 1
        assert a["coins"] == 4

    def test_rejects_major_unowned_and_bad_target(self):
        s = effect_state()
        a = P(s, 0)
        a["cards"] = {"moving_company": 1, "stadium": 1, "cafe": 1}
        fire(s, 9)
        # Major card
        assert handle_action(s, 0, {"event": "moving_company_pick",
                                    "card_id": "stadium", "target_seat": 1}) == {}
        # not owned
        assert handle_action(s, 0, {"event": "moving_company_pick",
                                    "card_id": "forest", "target_seat": 1}) == {}
        # target is self
        assert handle_action(s, 0, {"event": "moving_company_pick",
                                    "card_id": "cafe", "target_seat": 0}) == {}
        # target doesn't exist
        assert handle_action(s, 0, {"event": "moving_company_pick",
                                    "card_id": "cafe", "target_seat": 99}) == {}
        assert s["phase"] == "moving_company"             # still awaiting a valid pick

    def test_no_other_player_does_nothing(self):
        s = make(BASE_SHARP_GAME, num_players=1)
        a = P(s, 0)
        a["cards"] = {"moving_company": 1, "cafe": 1}
        a["coins"] = 0
        fire(s, 9)
        assert s["phase"] == "build"                      # no target → no-op
        assert card_count(a, "moving_company") == 1 and a["coins"] == 0

    def test_multi_copy_two_gives(self):
        s = effect_state()
        a, opp = P(s, 0), P(s, 1)
        a["cards"] = {"moving_company": 2, "cafe": 2}
        fire(s, 9)
        handle_action(s, 0, {"event": "moving_company_pick", "card_id": "cafe", "target_seat": 1})
        assert s["phase"] == "moving_company"             # one give left → re-prompt
        handle_action(s, 0, {"event": "moving_company_pick", "card_id": "cafe", "target_seat": 1})
        assert s["phase"] == "build"
        assert card_count(opp, "cafe") == 2 and card_count(a, "cafe") == 0
        assert a["coins"] == 8

    def test_renovation_limits_gives_to_active_copies(self):
        s = effect_state()
        a, opp = P(s, 0), P(s, 1)
        a["cards"] = {"moving_company": 2, "cafe": 2}
        a["renovation"] = {"moving_company": 1}           # 1 closed → 1 active give
        fire(s, 9)
        handle_action(s, 0, {"event": "moving_company_pick", "card_id": "cafe", "target_seat": 1})
        assert s["phase"] == "build"                      # only one give this roll
        assert card_count(opp, "cafe") == 1 and a["coins"] == 4

    def test_via_roll_handler(self, force_rolls):
        s = effect_state()
        a, opp = P(s, 0), P(s, 1)
        set_built(a, ["train_station"])                   # needed to roll 2 dice
        a["cards"] = {"moving_company": 1, "cafe": 1}
        force_rolls(4, 5)                                 # → 9
        handle_action(s, 0, {"event": "roll", "dice_count": 2})
        assert s["phase"] == "moving_company"
        handle_action(s, 0, {"event": "moving_company_pick", "card_id": "cafe", "target_seat": 1})
        assert card_count(opp, "cafe") == 1 and a["coins"] == 4
