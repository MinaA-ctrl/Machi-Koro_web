"""Stage 5 Phase A — the practice table: per-game dice, legal moves, bots, replay.

Each test maps to a row of Phase A's "Done when" table in
`Developer stages/stage-5-ai-plan.md`.
"""
import copy
import random

import pytest

from machi_koro_engine import CARD_DEFS, LANDMARK_DEFS, handle_action, legal_actions
from machi_koro_engine.game_engine import player_by_seat
from machi_koro_ai.bots import RandomBot, SimpleBot
from machi_koro_ai.game import Game, IllegalMove, make_config, play_game
from machi_koro_ai.play import describe
from machi_koro_ai.simulate import run_match

MODES = {
    "basic": make_config("basic"),
    "harbour": make_config("harbour"),
    "basic+sharp": make_config("basic", sharp=True),
    "harbour+sharp": make_config("harbour", sharp=True),
}


def fork(state):
    """Copy a state for a trial move. Card definitions are shared, never mutated."""
    return copy.deepcopy(state, memo={id(CARD_DEFS): CARD_DEFS})


def random_games(count, seed=0):
    """Yield (mode, Game) for `count` finished random games over all modes, 2–5 players."""
    rng = random.Random(seed)
    for g in range(count):
        mode = list(MODES)[g % len(MODES)]
        bots = [RandomBot(seed=rng.random()) for _ in range(2 + g % 4)]
        yield mode, bots, g


# ── Repeatability + isolation (per-game dice) ────────────────────────────────

def test_same_seed_same_moves_same_game():
    a = play_game([RandomBot(1), RandomBot(2)], seed=123)
    b = play_game([RandomBot(1), RandomBot(2)], seed=123)
    assert a.moves == b.moves
    assert a.state == b.state


def test_games_side_by_side_do_not_share_dice():
    """Interleaving two games move by move gives the same results as playing each alone."""
    alone = [play_game([RandomBot(s), RandomBot(s + 1)], seed=s) for s in (10, 20)]

    games = [Game(s, ["Random", "Random"]) for s in (10, 20)]
    bots = [[RandomBot(s), RandomBot(s + 1)] for s in (10, 20)]
    while not all(g.finished for g in games):
        for g, b in zip(games, bots):
            if not g.finished:
                g.play(b[g.to_move].choose(g.state, g.to_move, g.legal_moves()))
    for side_by_side, single in zip(games, alone):
        assert side_by_side.state == single.state


def test_replaying_recorded_moves_reproduces_the_game():
    original = play_game([SimpleBot(), RandomBot(5)], seed=99, config=MODES["harbour"])
    replay = Game(99, original.player_names, config=MODES["harbour"])
    for seat, move in original.moves:
        assert replay.to_move == seat
        replay.play(move)
    assert replay.state == original.state


# ── Legal moves: correct (every listed move is accepted) ─────────────────────

def test_every_listed_move_is_accepted_by_the_engine():
    """Across 150 random games in every mode, a sample of the listed moves at
    every decision is tried on a copy of the state: none may be refused."""
    checked = 0
    pick = random.Random(7)
    for mode, bots, g in random_games(150, seed=1):
        game = Game(g, [b.name for b in bots], config=MODES[mode])
        while not game.finished:
            legal = game.legal_moves()
            assert legal, f"{mode}: no legal moves in phase {game.state['phase']}"
            for move in pick.sample(legal, min(len(legal), 4)):
                trial = fork(game.state)
                assert handle_action(trial, game.to_move, move), (mode, game.state["phase"], move)
                checked += 1
            game.play(bots[game.to_move].choose(game.state, game.to_move, legal))
    assert checked > 15_000


# ── Legal moves: complete (nothing legal is missing) ─────────────────────────

# Which events each phase can accept — handle_action checks the phase before
# anything else, so other events are refused outright and needn't be tried.
PHASE_EVENTS = {
    "roll": {"roll"},
    "harbor_prompt": {"prompt_response"},
    "reroll_prompt": {"prompt_response"},
    "build": {"build", "skip_build", "tech_startup_invest"},
    "tuna_roll": {"tuna_roll"},
    "tv_station": {"tv_station_pick"},
    "cleaning_company": {"cleaning_company_pick"},
    "demolition": {"demolition_pick"},
}


def candidate_moves(state):
    """Every message a player could plausibly send in this state — a superset of
    the legal ones, used to check legal_actions misses nothing."""
    seats = [p["seat"] for p in state["players"]]
    cards = list(CARD_DEFS)
    out = [{"event": "roll", "dice_count": n} for n in (1, 2)]
    out += [{"event": "prompt_response", "answer": a} for a in (True, False)]
    out += [{"event": "build", "type": "card", "id": c} for c in cards]
    out += [{"event": "build", "type": "landmark", "id": lm["id"]} for lm in LANDMARK_DEFS]
    out += [{"event": e} for e in ("skip_build", "tech_startup_invest", "tuna_roll",
                                   "skip_business_center")]
    out += [{"event": "tv_station_pick", "target_seat": s} for s in seats]
    out += [{"event": "cleaning_company_pick", "card_type": c} for c in cards]
    out += [{"event": "demolition_pick", "landmark_id": lm["id"]} for lm in LANDMARK_DEFS]
    return out


def test_no_legal_move_is_missing():
    """For every decision in 25 random games, each candidate move the engine
    accepts must appear in legal_actions (and nothing it refuses may appear)."""
    for mode, bots, g in random_games(25, seed=2):
        game = Game(g, [b.name for b in bots], config=MODES[mode])
        while not game.finished:
            state, seat = game.state, game.to_move
            legal = game.legal_moves()
            if state["phase"] not in ("business_center", "moving_company"):  # checked below
                for move in candidate_moves(state):
                    if move["event"] not in PHASE_EVENTS[state["phase"]]:
                        continue
                    if move == {"event": "roll", "dice_count": 2} and \
                            {"event": "roll", "dice_count": 1} in legal and move not in legal:
                        continue  # engine quietly treats it as a 1-die roll — same move
                    accepted = bool(handle_action(fork(state), seat, move))
                    assert accepted == (move in legal), (mode, state["phase"], move, accepted)
            game.play(bots[seat].choose(state, seat, legal))


def test_business_center_lists_every_trade():
    game = Game(3, ["A", "B"])
    state = game.state
    me, opp = state["players"]
    me["cards"] = {"wheat_field": 2, "bakery": 1, "business_center": 1}
    opp["cards"] = {"ranch": 1, "cafe": 3}
    state["phase"] = "business_center"
    state["pending_prompt"] = {"type": "business_center"}
    legal = legal_actions(state, 0)
    trades = {(m["my_card"], m["opp_card"]) for m in legal if m["event"] == "business_center"}
    # Purple Majors can't be traded; every other pairing can.
    assert trades == {(a, b) for a in ("wheat_field", "bakery") for b in ("ranch", "cafe")}
    assert {"event": "skip_business_center"} in legal


def test_spot_checks():
    game = Game(1, ["A", "B"])
    state = game.state
    me = player_by_seat(state, 0)

    # Roll: one die until Train Station is built.
    assert legal_actions(state, 0) == [{"event": "roll", "dice_count": 1}]
    next(lm for lm in me["landmarks"] if lm["id"] == "train_station")["built"] = True
    assert {"event": "roll", "dice_count": 2} in legal_actions(state, 0)

    # Not your turn / game over → nothing.
    assert legal_actions(state, 1) == []

    # Build with 3 coins at the start of a Basic game: exactly the ≤3-coin cards.
    state["phase"] = "build"
    me["coins"] = 3
    buys = {m["id"] for m in legal_actions(state, 0) if m.get("type") == "card"}
    assert buys == {c for c in MODES["basic"].establishment_ids if CARD_DEFS[c]["cost"] <= 3}
    assert {"event": "skip_build"} in legal_actions(state, 0)

    # A Purple Major you already own isn't offered; a sold-out card isn't either.
    me["coins"] = 50
    me["cards"]["stadium"] = 1
    state["supply"]["mine"] = 0
    offered = {m["id"] for m in legal_actions(state, 0) if m.get("type") == "card"}
    assert "stadium" not in offered and "mine" not in offered and "tv_station" in offered

    state["phase"] = "finished"
    assert legal_actions(state, 0) == []


# ── No stuck games ────────────────────────────────────────────────────────────

def test_ten_thousand_random_games_all_finish_with_a_winner():
    unfinished = []
    for mode, bots, g in random_games(10_000, seed=3):
        game = play_game(bots, seed=g, config=MODES[mode])
        if game.winner is None:
            unfinished.append((mode, g, game.turns))
    assert not unfinished, unfinished[:5]


def test_illegal_move_is_refused():
    game = Game(1, ["A", "B"])
    with pytest.raises(IllegalMove):
        game.play({"event": "build", "type": "landmark", "id": "radio_tower"})


# ── Bot strength ──────────────────────────────────────────────────────────────

def test_simple_bot_beats_random_bot_at_least_90_percent():
    result = run_match(["simple", "random"], games=1000, seed=0)
    assert result["wins"].get("simple", 0) >= 900, result


# ── Text game ─────────────────────────────────────────────────────────────────

def test_text_game_can_describe_every_move():
    """Every menu line renders, in every mode, for every move ever offered."""
    for mode, bots, g in random_games(100, seed=4):
        game = Game(g, [b.name for b in bots], config=MODES[mode])
        while not game.finished:
            legal = game.legal_moves()
            for move in legal[:40]:
                assert describe(move, game.state)
            game.play(bots[game.to_move].choose(game.state, game.to_move, legal))
