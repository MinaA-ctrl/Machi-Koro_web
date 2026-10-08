"""SimpleBot — hand-written beginner strategy (no learning).

The plan, roughly how a new human player thinks:
  * Build a landmark whenever one is affordable (most expensive first).
  * Otherwise buy income cards from a priority list, each up to a cap; factories
    only once their feeder cards are owned.
  * Save instead of buying when the next landmark is nearly affordable.
  * Roll 2 dice once the cards that pay on 7+ out-earn the ones paying on 1–6.
  * Radio Tower: reroll a roll that pays nothing. Harbor: +2 if it pays more.
  * TV Station: rob the richest opponent. Business Center: skip the trade.
"""
from machi_koro_engine import CARD_DEFS
from machi_koro_engine.game_engine import (
    card_count, has_landmark, player_by_seat, _richest_opponent,
)

from .base import Bot

# Chance of each total with one die / two dice.
P_ONE = {t: 1 / 6 for t in range(1, 7)}
P_TWO = {t: (6 - abs(t - 7)) / 36 for t in range(2, 13)}

WHEAT = ("wheat_field", "apple_orchard", "flower_orchard", "corn_field")

# (card, cap, condition on my cards) — earlier = preferred.
BUY_PRIORITY = [
    ("cheese_factory", 2, lambda me: card_count(me, "ranch") >= 2),
    ("furniture_factory", 2, lambda me: card_count(me, "forest") + card_count(me, "mine") >= 2),
    ("mine", 2, lambda me: has_landmark(me, "train_station")),
    ("apple_orchard", 2, lambda me: has_landmark(me, "train_station")),
    ("family_restaurant", 2, lambda me: has_landmark(me, "train_station")),
    ("convenience_store", 3, lambda me: True),
    ("ranch", 3, lambda me: True),
    ("bakery", 3, lambda me: True),
    ("wheat_field", 2, lambda me: True),
    ("cafe", 2, lambda me: True),
    ("forest", 2, lambda me: True),
    ("stadium", 1, lambda me: has_landmark(me, "train_station")),
    ("tv_station", 1, lambda me: has_landmark(me, "train_station")),
]

# Start saving when this close (in coins) to the cheapest landmark still missing.
SAVE_WINDOW = 4


def own_turn_income(me, roll):
    """Rough coins `me` earns from their own blue/green cards on `roll` (bank only)."""
    def has(cid):
        return card_count(me, cid)

    payout = {
        "wheat_field": 1, "ranch": 1, "forest": 1, "mine": 5, "apple_orchard": 3,
        "bakery": 1, "convenience_store": 3,
        "cheese_factory": 3 * has("ranch"),
        "furniture_factory": 3 * (has("forest") + has("mine")),
        "farmers_market": 2 * sum(has(c) for c in WHEAT),
    }
    total = 0
    for cid, per_copy in payout.items():
        if roll in CARD_DEFS[cid]["dice"]:
            total += per_copy * has(cid)
    return total


def expected_income(me, odds):
    return sum(p * own_turn_income(me, t) for t, p in odds.items())


class SimpleBot(Bot):
    name = "Simple"

    def choose(self, state, seat, legal_moves):
        me = player_by_seat(state, seat)
        phase = state["phase"]
        pick = {
            "roll": self._roll,
            "reroll_prompt": self._reroll,
            "harbor_prompt": self._harbor,
            "tv_station": self._tv_station,
            "business_center": self._skip_trade,
            "build": self._build,
        }.get(phase)
        move = pick(state, me, legal_moves) if pick else None
        return move if move in legal_moves else legal_moves[0]

    # ── dice ──────────────────────────────────────────────────────────────────

    def _roll(self, state, me, moves):
        two = {"event": "roll", "dice_count": 2}
        if two in moves and expected_income(me, P_TWO) > expected_income(me, P_ONE):
            return two
        return {"event": "roll", "dice_count": 1}

    def _reroll(self, state, me, moves):
        pays = own_turn_income(me, state["last_roll"]) > 0
        return {"event": "prompt_response", "answer": not pays}

    def _harbor(self, state, me, moves):
        roll = state["pending_prompt"]["roll"]
        better = own_turn_income(me, roll + 2) > own_turn_income(me, roll)
        return {"event": "prompt_response", "answer": better}

    # ── prompts ───────────────────────────────────────────────────────────────

    def _tv_station(self, state, me, moves):
        target = _richest_opponent(state)
        return {"event": "tv_station_pick", "target_seat": target["seat"]}

    def _skip_trade(self, state, me, moves):
        return {"event": "skip_business_center"}

    # ── building ──────────────────────────────────────────────────────────────

    def _build(self, state, me, moves):
        landmarks = [m for m in moves if m.get("type") == "landmark"]
        if landmarks:
            cost = {lm["id"]: lm["cost"] for lm in me["landmarks"]}
            return max(landmarks, key=lambda m: cost[m["id"]])

        missing = [lm["cost"] for lm in me["landmarks"] if not lm["built"]]
        saving = missing and min(missing) - me["coins"] <= SAVE_WINDOW
        buyable = {m["id"]: m for m in moves if m.get("type") == "card"}
        for card_id, cap, wanted in BUY_PRIORITY:
            if card_id not in buyable or card_count(me, card_id) >= cap or not wanted(me):
                continue
            # While saving, only buy if the next landmark stays within reach.
            if saving and me["coins"] - CARD_DEFS[card_id]["cost"] < min(missing) - SAVE_WINDOW:
                continue
            return buyable[card_id]
        return {"event": "skip_build"}
