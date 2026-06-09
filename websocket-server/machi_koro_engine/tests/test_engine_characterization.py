"""TASK-005 — Engine characterization test harness.

These tests lock in the *current* behavior of game_engine.py so the Stage 1
refactor can't silently change card math. They assert what the code does today,
not an idealized rulebook. Where current behavior is arguably non-standard it is
noted in a comment but still asserted as-is (that's the point of characterization).

Coverage map (AC bullets from sprint-1-handoffs/qa.md):
  Blue payouts ............ TestBluePrimary
  Green payouts/mult ...... TestGreenSecondary
  Red restaurants + CCW ... TestRedRestaurant
  Purple majors ........... TestPurpleMajor
  Shopping Mall bonus ..... TestShoppingMall
  Tax Office rounding ..... TestPurpleMajor.test_tax_office_*
  City Hall floor ......... TestCityHall
  Win condition ........... TestWinCondition
  Count-based multipliers . TestGreenSecondary
  Tuna Boat + Harbor ...... TestTunaBoat
  Deterministic rolls ..... TestDeterminism
  Build / supply rules .... TestBuild
"""
import machi_koro_engine.game_engine as ge
from machi_koro_engine.game_engine import create_initial_state, resolve_cards, handle_action, check_win


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_state(num_players=2):
    info = [{"seat": i, "display_name": f"P{i}"} for i in range(num_players)]
    return create_initial_state(info)


def P(state, seat):
    return next(p for p in state["players"] if p["seat"] == seat)


def clear_all_cards(state):
    """Strip the default {wheat_field, bakery} so each test isolates its cards."""
    for p in state["players"]:
        p["cards"] = {}


def build_landmark(player, lm_id):
    for lm in player["landmarks"]:
        if lm["id"] == lm_id:
            lm["built"] = True


# ── Blue (Primary) — pays every owner on any player's roll ────────────────────

class TestBluePrimary:
    def test_wheat_field_pays_one_per_copy_on_1(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"wheat_field": 3}; a["coins"] = 0
        resolve_cards(s, 1)
        assert a["coins"] == 3  # 3 copies x 1

    def test_ranch_pays_one_per_copy_on_2(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"ranch": 2}; a["coins"] = 0
        resolve_cards(s, 2)
        assert a["coins"] == 2

    def test_forest_pays_one_per_copy_on_5(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"forest": 2}; a["coins"] = 0
        resolve_cards(s, 5)
        assert a["coins"] == 2

    def test_mine_pays_five_per_copy_on_9(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"mine": 1}; a["coins"] = 0
        resolve_cards(s, 9)
        assert a["coins"] == 5

    def test_apple_orchard_pays_three_per_copy_on_10(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"apple_orchard": 2}; a["coins"] = 0
        resolve_cards(s, 10)
        assert a["coins"] == 6

    def test_flower_garden_pays_one_per_copy_on_4(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"flower_garden": 2}; a["coins"] = 0
        resolve_cards(s, 4)
        assert a["coins"] == 2

    def test_mackerel_boat_pays_three_per_copy_with_harbor_on_8(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"mackerel_boat": 2}; a["coins"] = 0
        build_landmark(a, "harbor")
        resolve_cards(s, 8)
        assert a["coins"] == 6  # 2 x 3

    def test_mackerel_boat_pays_nothing_without_harbor(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"mackerel_boat": 2}; a["coins"] = 5  # non-zero so City Hall stays out of it
        resolve_cards(s, 8)
        assert a["coins"] == 5  # requires_landmark harbor not met -> no payout

    def test_blue_pays_all_owners_not_just_active(self):
        # Blue activates on anyone's turn: a non-active owner still gets paid.
        s = make_state(2); clear_all_cards(s)
        active = P(s, 0); active["coins"] = 0
        opp = P(s, 1); opp["cards"] = {"wheat_field": 1}; opp["coins"] = 0
        resolve_cards(s, 1)
        assert opp["coins"] == 1


# ── Green (Secondary) — pays active player only ───────────────────────────────

class TestGreenSecondary:
    def test_bakery_pays_one_per_copy_on_3(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"bakery": 2}; a["coins"] = 0
        resolve_cards(s, 3)
        assert a["coins"] == 2

    def test_convenience_store_pays_three_per_copy_on_4(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"convenience_store": 2}; a["coins"] = 0
        resolve_cards(s, 4)
        assert a["coins"] == 6

    def test_cheese_factory_multiplies_by_ranch_count_on_7(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"cheese_factory": 1, "ranch": 2}; a["coins"] = 0
        resolve_cards(s, 7)
        assert a["coins"] == 6  # 1 copy x 2 ranches x 3

    def test_furniture_factory_multiplies_by_gear_count_on_8(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"furniture_factory": 1, "forest": 1, "mine": 1}; a["coins"] = 0
        resolve_cards(s, 8)
        assert a["coins"] == 6  # 1 x (forest+mine = 2) x 3

    def test_farmers_market_multiplies_by_wheat_symbol_count_on_11(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"farmers_market": 1, "wheat_field": 2}; a["coins"] = 0
        resolve_cards(s, 11)
        assert a["coins"] == 4  # 1 x 2 wheat-symbol cards x 2

    def test_flower_shop_multiplies_by_flower_garden_count_on_6(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"flower_shop": 1, "flower_garden": 3}; a["coins"] = 0
        resolve_cards(s, 6)
        assert a["coins"] == 3  # 1 x 3 flower gardens

    def test_food_warehouse_multiplies_by_cup_symbol_count_with_harbor_on_13(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"food_warehouse": 1, "cafe": 2}; a["coins"] = 0
        build_landmark(a, "harbor")
        resolve_cards(s, 13)
        assert a["coins"] == 4  # 1 x 2 cup-symbol cards x 2 (own cafe doesn't pay as Red to self)


# ── Red (Restaurant) — opponents take from active, counter-clockwise ──────────

class TestRedRestaurant:
    def test_cafe_takes_one_per_copy_on_3(self):
        s = make_state(2); clear_all_cards(s)
        active = P(s, 0); active["coins"] = 5
        opp = P(s, 1); opp["cards"] = {"cafe": 2}; opp["coins"] = 0
        resolve_cards(s, 3)
        assert active["coins"] == 3 and opp["coins"] == 2

    def test_family_restaurant_takes_two_per_copy_on_9(self):
        s = make_state(2); clear_all_cards(s)
        active = P(s, 0); active["coins"] = 5
        opp = P(s, 1); opp["cards"] = {"family_restaurant": 1}; opp["coins"] = 0
        resolve_cards(s, 9)
        assert active["coins"] == 3 and opp["coins"] == 2

    def test_sushi_bar_takes_three_per_copy_with_harbor_on_1(self):
        s = make_state(2); clear_all_cards(s)
        active = P(s, 0); active["coins"] = 5
        opp = P(s, 1); opp["cards"] = {"sushi_bar": 1}; opp["coins"] = 0
        build_landmark(opp, "harbor")
        resolve_cards(s, 1)
        assert active["coins"] == 2 and opp["coins"] == 3

    def test_hamburger_stand_takes_one_per_copy_on_8(self):
        s = make_state(2); clear_all_cards(s)
        active = P(s, 0); active["coins"] = 5
        opp = P(s, 1); opp["cards"] = {"hamburger_stand": 2}; opp["coins"] = 0
        resolve_cards(s, 8)
        assert active["coins"] == 3 and opp["coins"] == 2

    def test_pizza_joint_takes_one_per_copy_on_7(self):
        s = make_state(2); clear_all_cards(s)
        active = P(s, 0); active["coins"] = 5
        opp = P(s, 1); opp["cards"] = {"pizza_joint": 1}; opp["coins"] = 0
        resolve_cards(s, 7)
        assert active["coins"] == 4 and opp["coins"] == 1

    def test_red_resolves_counter_clockwise_when_payer_runs_out(self):
        # 3 players, active(0) has only 1 coin. CCW order from active is seat2, then
        # seat1. Seat2 (first) collects; seat1 (second) gets nothing — order matters.
        # Active then hits the City Hall floor (0 -> 1).
        s = make_state(3); clear_all_cards(s)
        active = P(s, 0); active["coins"] = 1
        s1 = P(s, 1); s1["cards"] = {"cafe": 1}; s1["coins"] = 0
        s2 = P(s, 2); s2["cards"] = {"cafe": 1}; s2["coins"] = 0
        resolve_cards(s, 3)
        assert s2["coins"] == 1   # paid first (counter-clockwise)
        assert s1["coins"] == 0   # nothing left to take
        assert active["coins"] == 1  # drained to 0, then City Hall floor +1

    def test_red_take_capped_by_active_coins(self):
        s = make_state(2); clear_all_cards(s)
        active = P(s, 0); active["coins"] = 1
        opp = P(s, 1); opp["cards"] = {"cafe": 2}; opp["coins"] = 0  # wants 2, only 1 available
        resolve_cards(s, 3)
        assert opp["coins"] == 1
        assert active["coins"] == 1  # 1 -> 0 then City Hall floor


# ── Purple (Major) — active player only ───────────────────────────────────────

class TestPurpleMajor:
    def test_stadium_takes_two_from_each_opponent_on_6(self):
        s = make_state(3); clear_all_cards(s)
        active = P(s, 0); active["cards"] = {"stadium": 1}; active["coins"] = 0
        o1 = P(s, 1); o1["coins"] = 5
        o2 = P(s, 2); o2["coins"] = 5
        resolve_cards(s, 6)
        assert active["coins"] == 4 and o1["coins"] == 3 and o2["coins"] == 3

    def test_publisher_takes_one_per_cup_or_bread_card_on_7(self):
        s = make_state(2); clear_all_cards(s)
        active = P(s, 0); active["cards"] = {"publisher": 1}; active["coins"] = 0
        opp = P(s, 1); opp["cards"] = {"cafe": 1, "bakery": 1}; opp["coins"] = 5  # 1 cup + 1 bread
        resolve_cards(s, 7)
        assert active["coins"] == 2 and opp["coins"] == 3

    def test_tax_office_takes_half_rounded_down_on_8(self):
        s = make_state(3); clear_all_cards(s)
        active = P(s, 0); active["cards"] = {"tax_office": 1}; active["coins"] = 0
        rich = P(s, 1); rich["coins"] = 11      # 11 // 2 = 5
        poor = P(s, 2); poor["coins"] = 9       # < 10 -> exempt
        resolve_cards(s, 8)
        assert active["coins"] == 5
        assert rich["coins"] == 6               # 11 - 5
        assert poor["coins"] == 9               # untouched (10+ gate)

    def test_tax_office_exempts_opponent_below_ten(self):
        s = make_state(2); clear_all_cards(s)
        active = P(s, 0); active["cards"] = {"tax_office": 1}; active["coins"] = 0
        opp = P(s, 1); opp["coins"] = 9
        resolve_cards(s, 8)
        # Opponent (9 < 10) is exempt, so active collects no tax and, sitting at 0
        # coins after income, hits the City Hall floor (+1).
        assert active["coins"] == 1 and opp["coins"] == 9

    def test_tv_station_takes_five_from_chosen_target(self):
        s = make_state(2); clear_all_cards(s)
        active = P(s, 0); active["cards"] = {"tv_station": 1}; active["coins"] = 0
        opp = P(s, 1); opp["coins"] = 5
        s["phase"] = "tv_station"; s["last_roll"] = 6
        s["pending_prompt"] = {"type": "tv_station"}
        res = handle_action(s, 0, {"event": "tv_station_pick", "target_seat": 1})
        assert res.get("broadcast")
        assert active["coins"] == 5 and opp["coins"] == 0
        assert s["phase"] == "build"

    def test_business_center_swaps_two_establishments(self):
        s = make_state(2); clear_all_cards(s)
        active = P(s, 0); active["cards"] = {"business_center": 1, "wheat_field": 1}
        opp = P(s, 1); opp["cards"] = {"ranch": 1}
        s["phase"] = "business_center"
        s["pending_prompt"] = {"type": "business_center"}
        res = handle_action(s, 0, {
            "event": "business_center", "my_card": "wheat_field",
            "opp_seat": 1, "opp_card": "ranch",
        })
        assert res.get("broadcast")
        assert "ranch" in active["cards"] and "wheat_field" not in active["cards"]
        assert "wheat_field" in opp["cards"] and "ranch" not in opp["cards"]
        assert s["phase"] == "build"


# ── Shopping Mall +1 on cup / bread cards ─────────────────────────────────────

class TestShoppingMall:
    def test_mall_adds_one_per_bread_card_green(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"bakery": 2}; a["coins"] = 0
        build_landmark(a, "shopping_mall")
        resolve_cards(s, 3)
        assert a["coins"] == 4  # 2 base + 2 mall bonus

    def test_no_mall_no_bonus_green(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"bakery": 2}; a["coins"] = 0
        resolve_cards(s, 3)
        assert a["coins"] == 2

    def test_mall_adds_one_per_cup_card_red(self):
        # The restaurant owner's Shopping Mall boosts their own cup establishments.
        s = make_state(2); clear_all_cards(s)
        active = P(s, 0); active["coins"] = 5
        opp = P(s, 1); opp["cards"] = {"cafe": 1}; opp["coins"] = 0
        build_landmark(opp, "shopping_mall")
        resolve_cards(s, 3)
        assert opp["coins"] == 2 and active["coins"] == 3  # 1 base + 1 mall bonus


# ── City Hall floor ───────────────────────────────────────────────────────────

class TestCityHall:
    def test_active_at_zero_gets_one(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["coins"] = 0
        resolve_cards(s, 5)  # no card triggers
        assert a["coins"] == 1

    def test_no_floor_when_active_has_coins(self):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["coins"] = 3
        resolve_cards(s, 5)
        assert a["coins"] == 3


# ── Win condition ─────────────────────────────────────────────────────────────

class TestWinCondition:
    def test_check_win_fires_when_all_landmarks_built(self):
        s = make_state(2)
        a = P(s, 0)
        for lm in a["landmarks"]:
            lm["built"] = True
        assert check_win(s) is True
        assert s["phase"] == "finished"
        assert s["winner"] == 0
        assert "scores" in s

    def test_check_win_false_when_landmark_missing(self):
        s = make_state(2)
        a = P(s, 0)
        for lm in a["landmarks"]:
            lm["built"] = True
        build_landmark  # noqa - keep import obvious
        # leave one unbuilt
        next(lm for lm in a["landmarks"] if lm["id"] == "airport")["built"] = False
        assert check_win(s) is False
        assert s["phase"] != "finished"

    def test_build_last_landmark_triggers_win(self):
        s = make_state(2)
        a = P(s, 0)
        for lm in a["landmarks"]:
            lm["built"] = True
        next(lm for lm in a["landmarks"] if lm["id"] == "airport")["built"] = False
        a["coins"] = 30
        s["phase"] = "build"
        res = handle_action(s, 0, {"event": "build", "type": "landmark", "id": "airport"})
        assert res.get("broadcast")
        assert s["phase"] == "finished" and s["winner"] == 0


# ── Tuna Boat + Harbor interactive roll path ──────────────────────────────────

class TestTunaBoat:
    def test_tuna_roll_pays_two_dice_total_per_copy(self, force_rolls):
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"tuna_boat": 2}; a["coins"] = 0
        build_landmark(a, "harbor")
        s["phase"] = "tuna_roll"
        s["pending_prompt"] = {"type": "tuna_roll", "tuna_seats": [0]}
        force_rolls(3, 4)  # tuna two-dice total = 7
        res = handle_action(s, 0, {"event": "tuna_roll"})
        assert res.get("broadcast")
        assert a["coins"] == 14  # 2 copies x 7
        assert s["phase"] == "build"

    def test_tuna_full_path_through_harbor_prompt(self, force_rolls):
        # End-to-end: train station (2 dice) -> 6+6=12 -> Harbor prompt (decline)
        # -> Tuna interactive roll -> payout. Exercises the multi-phase flow.
        s = make_state(2); clear_all_cards(s)
        a = P(s, 0); a["cards"] = {"tuna_boat": 1}; a["coins"] = 0
        build_landmark(a, "harbor")
        build_landmark(a, "train_station")
        force_rolls(6, 6, 2, 5)  # initial 12, then tuna 2+5=7

        r1 = handle_action(s, 0, {"event": "roll", "dice_count": 2})
        assert s["phase"] == "harbor_prompt" and r1.get("prompt")

        handle_action(s, 0, {"event": "prompt_response", "answer": False})
        assert s["phase"] == "tuna_roll"

        handle_action(s, 0, {"event": "tuna_roll"})
        # The roll-12 income step pays nothing, so active hits the City Hall floor
        # (+1) during resolve_cards; the tuna roll (2+5=7) then adds 7 -> 8 total.
        assert a["coins"] == 8
        assert s["phase"] == "build"


# ── Deterministic (seeded) rolls ──────────────────────────────────────────────

class TestDeterminism:
    def test_seed_makes_roll_die_reproducible(self):
        ge.seed(12345)
        first = [ge.roll_die() for _ in range(30)]
        ge.seed(12345)
        second = [ge.roll_die() for _ in range(30)]
        assert first == second
        assert all(1 <= d <= 6 for d in first)

    def test_seeded_handle_action_roll_is_reproducible(self):
        s1 = make_state(2)
        s2 = make_state(2)
        ge.seed(99)
        handle_action(s1, 0, {"event": "roll"})
        ge.seed(99)
        handle_action(s2, 0, {"event": "roll"})
        assert s1["last_roll"] == s2["last_roll"]
        assert 1 <= s1["last_roll"] <= 6


# ── Build / supply rules ──────────────────────────────────────────────────────

class TestBuild:
    def test_build_card_spends_coins_and_decrements_supply(self):
        s = make_state(2)
        a = P(s, 0); a["coins"] = 5
        s["phase"] = "build"
        before = s["supply"]["convenience_store"]
        res = handle_action(s, 0, {"event": "build", "type": "card", "id": "convenience_store"})
        assert res.get("broadcast")
        assert a["coins"] == 3  # cost 2
        assert a["cards"].get("convenience_store") == 1
        assert s["supply"]["convenience_store"] == before - 1

    def test_build_rejected_when_insufficient_coins(self):
        s = make_state(2)
        a = P(s, 0); a["coins"] = 0
        s["phase"] = "build"
        before_supply = s["supply"]["mine"]
        res = handle_action(s, 0, {"event": "build", "type": "card", "id": "mine"})
        assert res == {}  # no-op
        assert a["coins"] == 0 and "mine" not in a["cards"]
        assert s["supply"]["mine"] == before_supply

    def test_purple_major_capped_at_one_per_player(self):
        s = make_state(2)
        a = P(s, 0); a["coins"] = 20; a["cards"]["stadium"] = 1
        s["phase"] = "build"
        before = s["supply"]["stadium"]
        res = handle_action(s, 0, {"event": "build", "type": "card", "id": "stadium"})
        assert res == {}  # max_per_player == 1 blocks the second copy
        assert a["coins"] == 20 and a["cards"]["stadium"] == 1
        assert s["supply"]["stadium"] == before

    def test_wrong_seat_action_is_ignored(self):
        s = make_state(2)
        s["phase"] = "roll"
        res = handle_action(s, 1, {"event": "roll"})  # seat 1 acting on seat 0's turn
        assert res == {}
