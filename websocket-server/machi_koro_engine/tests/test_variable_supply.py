"""Stage 1 — Variable Supply (Phase E).

Only 10 distinct establishment types are face-up at once; selling one out reveals
the next from a shuffled, seedable deck. Default-off (any non-Sharp config, or a
Sharp config with variable_supply=False) is byte-identical to the classic supply.

Determinism: all randomness is the deck shuffle, through the engine's seedable
_rng. seed(N) before create_initial_state makes setup reproducible.
"""
from collections import Counter

import pytest

from machi_koro_engine.game_engine import create_initial_state, handle_action, seed, _draw_to_market
from machi_koro_engine.game_config import (
    build_config, config_for, BASE_GAME, HARBOUR_GAME, BASE_SHARP_GAME, HARBOUR_SHARP_GAME,
)
from machi_koro_engine.card_defs import CARD_DEFS


def info(n=2):
    return [{"seat": i, "display_name": f"P{i}"} for i in range(n)]


def make_vs(config=HARBOUR_SHARP_GAME, n=2, s=7):
    if s is not None:
        seed(s)
    return create_initial_state(info(n), config=config)


def total_copies(config, n):
    return sum(n if CARD_DEFS[c]["type"] == "Purple Major" else 6
               for c in config.establishment_ids)


def buy(state, cid, seat=0, coins=999):
    """Build one copy of `cid` as the active player (resets the build window, since
    a successful build advances the turn)."""
    state["active_seat"] = seat
    state["phase"] = "build"
    state["players"][seat]["coins"] = coins
    return handle_action(state, seat, {"event": "build", "type": "card", "id": cid})


# ── Flag defaults ────────────────────────────────────────────────────────────

class TestFlag:
    def test_defaults_on_for_sharp_off_otherwise(self):
        assert HARBOUR_GAME.variable_supply is False
        assert BASE_GAME.variable_supply is False
        assert HARBOUR_SHARP_GAME.variable_supply is True
        assert BASE_SHARP_GAME.variable_supply is True

    def test_override_either_way(self):
        assert build_config(HARBOUR_GAME, sharp=True, variable_supply=False).variable_supply is False
        assert build_config(BASE_GAME, sharp=False, variable_supply=True).variable_supply is True


# ── config_for: the (base, sharp, variable_supply) resolution seam ───────────
# This is what main.py persists against (table-start AND rematch). The three flags
# are independent; an explicit variable_supply overrides build_config's default.

class TestConfigForFlag:
    def test_default_supply_mode_returns_singletons(self):
        # variable_supply=None keeps the canonical singleton (identity preserved).
        assert config_for("harbour", False, None) is HARBOUR_GAME
        assert config_for("harbour", True, None) is HARBOUR_SHARP_GAME
        # …and an explicit flag matching the default still returns the singleton.
        assert config_for("harbour", True, True) is HARBOUR_SHARP_GAME
        assert config_for("basic", False, False) is BASE_GAME

    def test_independent_of_sharp(self):
        # VS on, Sharp off — any base.
        c = config_for("harbour", False, True)
        assert c.variable_supply is True and c.sharp is False
        assert config_for("basic", False, True).variable_supply is True
        # VS off on a Sharp config (classic supply + Sharp pool).
        c2 = config_for("harbour", True, False)
        assert c2.variable_supply is False and c2.sharp is True

    def test_db_int_flags(self):
        # The DB hands back 0/1 ints; truthiness must work.
        assert config_for("harbour", 1, 1) is HARBOUR_SHARP_GAME
        assert config_for("harbour", 0, 0) is HARBOUR_GAME
        assert config_for("harbour", 0, 1).variable_supply is True

    def test_state_reflects_choice(self):
        # End-to-end: config_for → create_initial_state. 'deck' present iff VS on.
        on = create_initial_state(info(2), config=config_for("harbour", False, True))
        off = create_initial_state(info(2), config=config_for("harbour", False, False))
        assert "deck" in on and len(on["supply"]) == 10
        assert "deck" not in off


# ── The shared draw rule (setup == refill) ───────────────────────────────────

class TestDrawRule:
    def test_dupes_stack_and_dont_count_toward_ten(self):
        # Draw from the end; a duplicate stacks onto its type and the loop keeps
        # going. Deck smaller than 10 distinct → stop when empty.
        supply = {}
        deck = ["a", "a", "b", "c"]            # pop order: c, b, a, a
        _draw_to_market(deck, supply)
        assert supply == {"c": 1, "b": 1, "a": 2}
        assert deck == []

    def test_stops_at_ten_distinct(self):
        supply = {}
        deck = [str(i) for i in range(20)]     # 20 distinct
        _draw_to_market(deck, supply)
        assert len(supply) == 10
        assert len(deck) == 10                 # only drew down to the 10th distinct


# ── Setup ────────────────────────────────────────────────────────────────────

class TestSetup:
    def test_deals_10_distinct(self):
        s = make_vs(HARBOUR_SHARP_GAME, s=1)
        assert "deck" in s
        assert len(s["supply"]) == 10                       # 10 distinct face-up
        assert len(s["market"]) == 10
        assert {c["id"] for c in s["market"]} == set(s["supply"])

    def test_conserves_all_copies(self):
        s = make_vs(HARBOUR_SHARP_GAME, n=2, s=2)
        in_play = sum(s["supply"].values()) + len(s["deck"])
        assert in_play == total_copies(HARBOUR_SHARP_GAME, 2)

    def test_purple_uses_num_players_copies(self):
        s = make_vs(HARBOUR_SHARP_GAME, n=3, s=5)
        pool = Counter(s["deck"])
        for cid, cnt in s["supply"].items():
            pool[cid] += cnt
        assert pool["tech_startup"] == 3       # Purple Major → num_players
        assert pool["park"] == 3
        assert pool["wheat_field"] == 6        # regular → 6


# ── Buy + refill ─────────────────────────────────────────────────────────────

class TestBuyRefill:
    def test_only_visible_types_are_buildable(self):
        s = make_vs(HARBOUR_SHARP_GAME, s=9)
        hidden = next(c for c in s["deck"] if c not in s["supply"])
        out = buy(s, hidden)
        assert out == {}                       # not face-up → rejected
        assert hidden not in s["players"][0]["cards"]

    def test_buy_last_copy_refills_with_new_type(self):
        s = make_vs(HARBOUR_SHARP_GAME, s=2)
        cid = next(c for c in s["supply"] if CARD_DEFS[c]["type"] != "Purple Major")
        copies = s["supply"][cid]
        deck_before = len(s["deck"])
        for _ in range(copies):
            buy(s, cid)
        # The sold-out stack was replaced; board is back to 10 distinct (deck had plenty)
        assert len(s["supply"]) == 10
        assert deck_before - len(s["deck"]) >= 1     # at least one card drawn to refill
        assert s["players"][0]["cards"][cid] == copies

    def test_multi_copy_buy_refills_only_when_count_hits_zero(self):
        s = make_vs(HARBOUR_SHARP_GAME, s=3)
        cid = next(c for c in s["supply"]
                   if CARD_DEFS[c]["type"] != "Purple Major" and s["supply"][c] >= 2)
        before_types = set(s["supply"])
        buy(s, cid)                            # one of several copies
        assert set(s["supply"]) == before_types   # still visible → no refill yet
        assert s["supply"][cid] >= 1

    def test_type_can_reenter_after_refill(self):
        # Edge case #3: a sold-out type can be drawn again from the deck.
        s = make_vs(HARBOUR_SHARP_GAME, s=3)
        cid = next(c for c in s["supply"] if CARD_DEFS[c]["type"] != "Purple Major")
        s["deck"].append(cid)                  # force it to the top (drawn first on refill)
        s["supply"][cid] = 1                   # down to its last copy
        buy(s, cid)
        assert cid in s["supply"]              # re-entered via refill
        assert len(s["supply"]) == 10

    def test_deck_exhaustion_leaves_fewer_than_10(self):
        s = make_vs(HARBOUR_SHARP_GAME, s=4)
        s["deck"] = []                         # simulate a drained late-game deck
        cid = next(c for c in s["supply"] if CARD_DEFS[c]["type"] != "Purple Major")
        s["supply"][cid] = 1
        buy(s, cid)                            # sells out, refill can't replace
        assert cid not in s["supply"]
        assert len(s["supply"]) == 9           # fewer than 10 is fine, no error


# ── Determinism ──────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_same_seed_same_setup(self):
        a = make_vs(HARBOUR_SHARP_GAME, s=7)
        b = make_vs(HARBOUR_SHARP_GAME, s=7)
        assert a["supply"] == b["supply"]
        assert a["deck"] == b["deck"]

    def test_different_seed_differs(self):
        a = make_vs(HARBOUR_SHARP_GAME, s=7)
        b = make_vs(HARBOUR_SHARP_GAME, s=8)
        assert a["deck"] != b["deck"]          # a full reshuffle differs across seeds

    def test_seeded_buy_sequence_reproduces_market(self):
        def run():
            s = make_vs(HARBOUR_SHARP_GAME, s=11)
            cid = next(c for c in s["supply"] if CARD_DEFS[c]["type"] != "Purple Major")
            for _ in range(s["supply"][cid]):
                buy(s, cid)
            return s["supply"], s["deck"]
        assert run() == run()                  # same seed + same buys ⇒ identical evolution


# ── Default-off byte-identity ────────────────────────────────────────────────

class TestDefaultOff:
    def test_no_deck_key_and_full_supply(self):
        s = create_initial_state(info(2), config=HARBOUR_GAME)
        assert "deck" not in s
        assert set(s["supply"]) == set(HARBOUR_GAME.establishment_ids)
        assert len(s["market"]) == len(HARBOUR_GAME.establishment_ids)

    def test_sharp_with_vs_off_is_classic(self):
        cfg = build_config(BASE_GAME, sharp=True, variable_supply=False)
        s = create_initial_state(info(2), config=cfg)
        assert "deck" not in s
        assert set(s["supply"]) == set(cfg.establishment_ids)

    def test_classic_state_byte_identical(self):
        # The full state dict for a default-off config is exactly the classic one.
        s = create_initial_state(info(2), config=HARBOUR_GAME)
        expected_keys = {
            "phase", "version", "active_seat", "last_roll", "last_dice", "doubles",
            "ap_active", "ap_used", "tech_invest_used", "interactive_active_copies",
            "pending_prompt", "players", "market", "supply", "card_defs", "winner",
            "game_seq", "log",
        }
        assert set(s) == expected_keys         # no 'deck', nothing extra
