"""S3.4/S3.5 — keyed events + interactive-prompt contract.

These lock in the *additive* Stage-3 surface the React frontend builds against:
  • every player-facing string is also a structured event (state['events']);
  • the English log is fully DERIVED from those events (i18n source of truth);
  • coin movement is an ordered payout stream (income / take / bank_pay);
  • the variable-supply market reveal is emitted as an explicit slot diff;
  • the four Sharp prompts expose a structured payload + a valid timeout default.

All deterministic (direct resolve_cards / scripted rolls), no transport/DB.
"""
import pytest

from machi_koro_engine import (
    create_initial_state, resolve_cards, handle_action,
    build_prompt_payload, default_response, config_for, events as ev,
)
from machi_koro_engine.game_config import HARBOUR_GAME, HARBOUR_SHARP_GAME
from machi_koro_engine.events import render_en, TOAST_ONLY, PAYOUT_TYPES, _RENDERERS


def info(n=2):
    return [{"seat": i, "display_name": f"P{i}", "user_id": i + 1} for i in range(n)]


def harbour(n=2):
    return create_initial_state(info(n), config=HARBOUR_GAME)


def sharp(n=2):
    return create_initial_state(info(n), config=HARBOUR_SHARP_GAME)


# ── i18n: log is derived from events; every type renders ──────────────────────

class TestKeyedLog:
    def test_initial_state_has_event_stream(self):
        s = harbour()
        assert s["events"] == [] and s["event_seq"] == 0

    def test_every_event_type_has_a_renderer(self):
        # Guards against shipping an event type with no EN render (would KeyError live).
        # The type constants on the module map 1:1 to the renderer table.
        type_consts = {v for k, v in vars(ev).items()
                       if k.isupper() and isinstance(v, str)}
        assert type_consts == set(_RENDERERS)

    def test_log_is_derived_from_events(self, force_rolls):
        # The English log == the EN render of every non-toast-only event, in order
        # (both capped at the log's 15). Proves state['log'] is a pure view of the
        # keyed stream — so localizing the stream localizes the whole log.
        s = sharp()
        force_rolls(1, 2, 3)
        handle_action(s, 0, {"event": "roll", "dice_count": 1})   # roll → income(s)
        handle_action(s, 0, {"event": "skip_build"})              # advance turn
        force_rolls(2)
        handle_action(s, 1, {"event": "roll", "dice_count": 1})
        logged = [render_en(e) for e in s["events"] if e["t"] not in TOAST_ONLY]
        assert logged[-15:] == s["log"]

    def test_roll_event_carries_dice_truth(self, force_rolls):
        s = harbour()
        force_rolls(3)
        handle_action(s, 0, {"event": "roll", "dice_count": 1})
        roll = next(e for e in s["events"] if e["t"] == ev.ROLL)
        assert roll["dice"] == [3] and roll["total"] == 3
        assert roll["dice_count"] == 1 and roll["doubles"] is False

    def test_two_die_mode_is_in_the_event(self, force_rolls):
        s = harbour()
        next(lm for lm in s["players"][0]["landmarks"] if lm["id"] == "train_station")["built"] = True
        force_rolls(4, 4)
        handle_action(s, 0, {"event": "roll", "dice_count": 2})
        roll = next(e for e in s["events"] if e["t"] == ev.ROLL)
        assert roll["dice"] == [4, 4] and roll["total"] == 8
        assert roll["dice_count"] == 2 and roll["doubles"] is True


# ── Coin transactions: ordered, structured payout stream ──────────────────────

class TestPayoutStream:
    def test_income_event_matches_card_math(self):
        s = harbour()
        active = s["players"][0]
        active["cards"]["wheat_field"] = active["cards"].get("wheat_field", 0)  # owned at start
        before = active["coins"]
        resolve_cards(s, 1)                                  # wheat_field hits on 1
        inc = [e for e in s["events"] if e["t"] == ev.INCOME and e["seat"] == 0]
        assert inc and inc[0]["source"] == "wheat_field" and inc[0]["amount"] == 1
        assert active["coins"] == before + 1

    def test_take_event_is_player_to_player(self):
        s = harbour()
        active, opp = s["players"][0], s["players"][1]
        opp["cards"]["cafe"] = 1                              # cafe (red) hits on 3
        active["coins"] = 5
        resolve_cards(s, 3)
        take = next(e for e in s["events"] if e["t"] == ev.TAKE)
        assert take["source"] == "cafe"
        assert take["taker_seat"] == 1 and take["payer_seat"] == 0
        assert take["amount"] == 1

    def test_bank_pay_event_for_loan_office(self):
        s = sharp()
        active = s["players"][0]
        active["cards"]["loan_office"] = 1                    # negative activation on 5/6
        active["coins"] = 10
        resolve_cards(s, 5)
        pay = next(e for e in s["events"] if e["t"] == ev.BANK_PAY)
        assert pay["source"] == "loan_office" and pay["amount"] == 2 and pay["seat"] == 0

    def test_payouts_are_ordered_and_sequenced(self):
        # Two opponents both with a cafe → two separate take events, strictly ordered
        # by seq, so the UI can sequence the coins flying out one after another.
        s = harbour(3)
        s["players"][0]["coins"] = 5
        s["players"][1]["cards"]["cafe"] = 1
        s["players"][2]["cards"]["cafe"] = 1
        resolve_cards(s, 3)
        takes = [e for e in s["events"] if e["t"] == ev.TAKE]
        assert len(takes) == 2
        seqs = [e["seq"] for e in takes]
        assert seqs == sorted(seqs) and len(set(seqs)) == 2
        assert all(e["t"] in PAYOUT_TYPES for e in takes)


# ── Variable-supply market reveal: explicit slot diff ─────────────────────────

class TestMarketReveal:
    def _vs_state(self):
        return create_initial_state(info(2), config=config_for("harbour", True, True))

    def test_buying_out_a_stack_emits_the_reveal_diff(self):
        s = self._vs_state()
        assert "deck" in s and len(s["supply"]) == 10
        # Pick a face-up type, force its stack to a single copy, and buy it out.
        target = next(cid for cid in s["supply"]
                      if s["card_defs"][cid]["type"] != "Purple Major")
        s["supply"][target] = 1
        s["phase"] = "build"
        s["active_seat"] = 0
        s["players"][0]["coins"] = 50
        s["players"][0]["cards"].pop(target, None)           # avoid max-per-player guards

        handle_action(s, 0, {"event": "build", "type": "card", "id": target})

        reveal = next(e for e in s["events"] if e["t"] == ev.MARKET_REVEAL)
        assert reveal["bought_card_id"] == target
        assert reveal["slot_emptied"] is True
        assert target not in s["supply"]                      # the slot really emptied
        # The revealed card(s) are new face-up types not present before the buy,
        # given explicitly so the UI never has to diff full state.
        assert reveal["revealed"]                              # ≥1 revealed (deck had cards)
        for cid in reveal["revealed"]:
            assert cid in s["supply"] and cid != target
        assert reveal["supply"] == {c: s["supply"][c] for c in s["supply"]}

    def test_classic_buy_emits_no_reveal(self):
        s = harbour()
        s["phase"] = "build"
        s["players"][0]["coins"] = 50
        s["supply"]["wheat_field"] = 1
        handle_action(s, 0, {"event": "build", "type": "card", "id": "wheat_field"})
        assert not any(e["t"] == ev.MARKET_REVEAL for e in s["events"])


# ── Interactive prompts: structured payload + valid timeout default ───────────

class TestPromptContract:
    def _force_phase(self, force_rolls, card_id, roll_faces, *, give_opp=None):
        """Build a Harbour+Sharp game and roll into the interactive phase for card_id."""
        s = sharp()
        active = s["players"][0]
        active["cards"][card_id] = 1
        next(lm for lm in active["landmarks"] if lm["id"] == "train_station")["built"] = True
        if give_opp:
            s["players"][1]["cards"][give_opp] = 1
        force_rolls(*roll_faces)
        handle_action(s, 0, {"event": "roll", "dice_count": 2})
        return s

    def test_no_prompt_when_none_pending(self):
        s = sharp()
        assert build_prompt_payload(s) is None and default_response(s) is None

    def test_cleaning_company_payload_and_default(self, force_rolls):
        s = self._force_phase(force_rolls, "cleaning_company", (3, 5), give_opp="cafe")  # 8
        assert s["phase"] == "cleaning_company"
        p = build_prompt_payload(s)
        assert p["type"] == "cleaning_company" and p["response_event"] == "cleaning_company_pick"
        assert "cafe" in p["params"]["targets"]
        assert p["default"]["card_type"] in p["params"]["targets"]
        # The default is a move the engine accepts and resolves.
        handle_action(s, 0, default_response(s))
        assert s["phase"] == "build"

    def test_demolition_payload_and_default(self, force_rolls):
        # Demolition is mandatory only with a demolishable (built, non-City-Hall)
        # landmark — give the active player Harbor so the prompt actually fires.
        s = sharp()
        active = s["players"][0]
        active["cards"]["demolition_company"] = 1
        next(lm for lm in active["landmarks"] if lm["id"] == "train_station")["built"] = True
        next(lm for lm in active["landmarks"] if lm["id"] == "harbor")["built"] = True
        force_rolls(2, 2)                                     # 4 → Demolition
        handle_action(s, 0, {"event": "roll", "dice_count": 2})
        assert s["phase"] == "demolition"
        p = build_prompt_payload(s)
        assert p["type"] == "demolition" and p["response_event"] == "demolition_pick"
        assert p["default"]["landmark_id"] in p["params"]["targets"]
        handle_action(s, 0, default_response(s))
        assert s["phase"] == "build"

    def test_moving_company_payload_and_default(self, force_rolls):
        s = self._force_phase(force_rolls, "moving_company", (4, 5))  # 9
        assert s["phase"] == "moving_company"
        p = build_prompt_payload(s)
        assert p["type"] == "moving_company" and p["response_event"] == "moving_company_pick"
        assert p["options"]["cards"] and p["options"]["target_seats"]
        d = default_response(s)
        assert d["card_id"] in p["params"]["giveable"] and d["target_seat"] in p["params"]["targets"]
        handle_action(s, 0, d)
        assert s["phase"] == "build"

    def test_tech_startup_is_not_a_prompt(self):
        # Tech Startup is an optional build-window action (invest 1, ≤1/turn), not a
        # server prompt — so it never produces a pending_prompt and needs no timeout.
        s = sharp()
        s["players"][0]["cards"]["tech_startup"] = 1
        s["players"][0]["coins"] = 3
        s["phase"] = "build"
        handle_action(s, 0, {"event": "tech_startup_invest"})
        assert s["pending_prompt"] is None
        inv = next(e for e in s["events"] if e["t"] == ev.TECH_INVEST)
        assert inv["total"] == 1

    def test_harbor_prompt_default_keeps_the_roll(self, force_rolls):
        s = harbour()
        next(lm for lm in s["players"][0]["landmarks"] if lm["id"] == "harbor")["built"] = True
        next(lm for lm in s["players"][0]["landmarks"] if lm["id"] == "train_station")["built"] = True
        force_rolls(5, 5)                                     # 10 → harbor prompt
        handle_action(s, 0, {"event": "roll", "dice_count": 2})
        p = build_prompt_payload(s)
        assert p["promptId"] == "harbor_bonus" and p["params"]["total_with_bonus"] == 12
        assert p["default"] == {"event": "prompt_response", "answer": False}
        handle_action(s, 0, default_response(s))             # decline → resolve at 10
        assert s["last_roll"] == 10

    def test_tv_station_default_targets_richest_opponent(self):
        s = harbour(3)
        s["players"][0]["cards"]["tv_station"] = 1
        s["players"][1]["coins"] = 3
        s["players"][2]["coins"] = 9
        s["phase"] = "tv_station"
        s["pending_prompt"] = {"type": "tv_station"}
        p = build_prompt_payload(s)
        assert p["default"]["target_seat"] == 2              # the 9-coin opponent
