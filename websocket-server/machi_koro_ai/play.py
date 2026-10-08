"""Play Machi Koro against a bot in the terminal.

    cd websocket-server
    python3 -m machi_koro_ai.play                      # you vs SimpleBot, Basic game
    python3 -m machi_koro_ai.play --opponent random    # an easier opponent
    python3 -m machi_koro_ai.play --second             # let the bot start
    python3 -m machi_koro_ai.play --replay machi_koro_ai/human_games/<file>.json

Type the number of a move and press Enter. Type q to quit (the game is still saved).
Every game is saved to machi_koro_ai/human_games/ (kept only on this computer).
"""
import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

from machi_koro_engine import CARD_DEFS, LANDMARK_DEFS
from machi_koro_engine import events as ev
from machi_koro_engine.game_engine import player_by_seat

from .bots import make_bot
from .game import Game, make_config

GAMES_DIR = Path(__file__).parent / "human_games"
LANDMARK_NAMES = {lm["id"]: lm["name"] for lm in LANDMARK_DEFS}


# ── text helpers ──────────────────────────────────────────────────────────────

def card_name(card_id):
    return CARD_DEFS[card_id]["name"] if card_id in CARD_DEFS else LANDMARK_NAMES.get(card_id, card_id)


def dice_text(dice):
    return ",".join(str(d) for d in dice)


def describe(move, state):
    """One menu line for a move."""
    e = move["event"]
    if e == "roll":
        return "Roll 2 dice" if move["dice_count"] == 2 else "Roll 1 die"
    if e == "prompt_response":
        if state["phase"] == "harbor_prompt":
            roll = state["pending_prompt"]["roll"]
            return f"Harbor: add +2 (make it {roll + 2})" if move["answer"] else f"Keep {roll}"
        return "Radio Tower: reroll" if move["answer"] else f"Keep {state['last_roll']}"
    if e == "build" and move["type"] == "card":
        c = CARD_DEFS[move["id"]]
        left = state["supply"].get(move["id"], 0)
        return (f"Buy {c['name']:<18} {c['cost']:>2} coins   dice {dice_text(c['dice']):<5} "
                f"{c['effect']}  ({left} left)")
    if e == "build" and move["type"] == "landmark":
        me = player_by_seat(state, state["active_seat"])
        lm = next(l for l in me["landmarks"] if l["id"] == move["id"])
        return f"Build {lm['name']:<16} {lm['cost']:>2} coins   ★ {lm['effect']}"
    if e == "skip_build":
        return "Build nothing this turn"
    if e == "tv_station_pick":
        target = player_by_seat(state, move["target_seat"])
        return f"Take 5 coins from {target['name']} (has {target['coins']})"
    if e == "skip_business_center":
        return "Don't trade"
    if e == "business_center":
        opp = player_by_seat(state, move["opp_seat"])
        return f"Give your {card_name(move['my_card'])} for {opp['name']}'s {card_name(move['opp_card'])}"
    if e == "tuna_roll":
        return "Roll 2 dice for Tuna Boats"
    return json.dumps(move)


def show_board(state):
    for p in state["players"]:
        marker = "▶" if p["seat"] == state["active_seat"] else " "
        cards = ", ".join(f"{card_name(c)} x{n}" if n > 1 else card_name(c)
                          for c, n in sorted(p["cards"].items(), key=lambda kv: CARD_DEFS[kv[0]]["dice"][0]))
        built = [l["name"] for l in p["landmarks"] if l["built"] and l["id"] != "city_hall"]
        todo = [f"{l['name']} ({l['cost']})" for l in p["landmarks"] if not l["built"]]
        print(f" {marker} {p['name']:<10} coins: {p['coins']:>3}")
        print(f"     cards:     {cards or '-'}")
        print(f"     landmarks: {', '.join(built) or '-'}   still to build: {', '.join(todo) or '-'}")


def print_new_events(state, since_seq):
    """Print the game log lines added since `since_seq`; return the new last seq."""
    last = since_seq
    for e in state.get("events", []):
        if e["seq"] <= since_seq:
            continue
        last = e["seq"]
        try:
            print(f"   · {ev.render_en(e)}")
        except KeyError:
            pass        # animation-only events have no text
    return last


def ask(prompt, n):
    """Ask for a number 1..n; returns the index, or None for quit."""
    while True:
        try:
            raw = input(prompt).strip().lower()
        except EOFError:
            return None
        if raw in ("q", "quit", "exit"):
            return None
        if raw.isdigit() and 1 <= int(raw) <= n:
            return int(raw) - 1
        print(f"   Please type a number from 1 to {n} (or q to quit).")


# ── human turn ────────────────────────────────────────────────────────────────

def choose_human_move(state, legal):
    if state["phase"] == "business_center" and len(legal) > 12:
        return choose_trade(state, legal)
    if len(legal) == 1:                     # nothing to decide — just confirm
        try:
            raw = input(f"\n   Press Enter to {describe(legal[0], state).lower()} (q to quit) ")
        except EOFError:
            return None
        return None if raw.strip().lower() in ("q", "quit", "exit") else legal[0]
    print()
    for i, m in enumerate(legal, 1):
        print(f"   {i:>2}) {describe(m, state)}")
    idx = ask("   Your choice: ", len(legal))
    return None if idx is None else legal[idx]


def choose_trade(state, legal):
    """Business Center can offer hundreds of trades — ask step by step instead."""
    print("\n   Business Center: you may swap one of your cards for an opponent's.")
    print("    1) Trade\n    2) Don't trade")
    idx = ask("   Your choice: ", 2)
    if idx is None:
        return None
    if idx == 1:
        return {"event": "skip_business_center"}
    trades = [m for m in legal if m["event"] == "business_center"]
    mine = sorted({m["my_card"] for m in trades})
    for i, c in enumerate(mine, 1):
        print(f"   {i:>2}) give your {card_name(c)}")
    i = ask("   Which card do you give? ", len(mine))
    if i is None:
        return None
    options = [m for m in trades if m["my_card"] == mine[i]]
    for j, m in enumerate(options, 1):
        print(f"   {j:>2}) {describe(m, state)}")
    j = ask("   Which card do you take? ", len(options))
    return None if j is None else options[j]


# ── save / replay ─────────────────────────────────────────────────────────────

def save_game(game, meta):
    GAMES_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = GAMES_DIR / f"{stamp}.json"
    record = {
        **meta,
        "seed": game.seed,
        "players": game.player_names,
        "winner": game.winner,
        "turns": game.turns,
        "moves": [[seat, move] for seat, move in game.moves],
    }
    path.write_text(json.dumps(record, indent=1))
    return path


def replay(path, delay):
    rec = json.loads(Path(path).read_text())
    game = Game(rec["seed"], rec["players"], config=make_config(rec["mode"], sharp=rec.get("sharp", False)))
    print(f"Replaying {path}: {' vs '.join(rec['players'])}\n")
    seq = 0
    for seat, move in rec["moves"]:
        if move["event"] == "roll":
            print(f"\n── {player_by_seat(game.state, seat)['name']}'s turn ──")
        game.play(move)
        seq = print_new_events(game.state, seq)
        time.sleep(delay)
    winner = game.winner
    print("\nResult:", f"{rec['players'][winner]} won" if winner is not None else "unfinished",
          f"after {game.turns} turns.")
    if game.winner != rec.get("winner"):
        print("WARNING: replay ended differently from the saved game.")


# ── main loop ─────────────────────────────────────────────────────────────────

def play(opponent, mode, human_first, delay, seed, name):
    bot = make_bot(opponent, seed=seed)
    bot_name = f"{bot.name}Bot"
    names = [name, bot_name] if human_first else [bot_name, name]
    human_seat = 0 if human_first else 1
    game = Game(seed, names, config=make_config(mode))
    meta = {"mode": mode, "sharp": False, "opponent": opponent, "human_seat": human_seat}

    print(f"\nMachi Koro ({game.config.name}) — {names[0]} vs {names[1]}. "
          f"Build all your landmarks first to win.  (q = quit)\n")
    seq = 0
    while not game.finished:
        state = game.state
        seat = game.to_move
        if state["phase"] == "roll":        # a new turn (or an Amusement Park extra turn)
            print(f"\n{'═' * 22} TURN {game.turns + 1}: {player_by_seat(state, seat)['name'].upper()} {'═' * 22}")
            show_board(state)
        legal = game.legal_moves()
        if seat == human_seat:
            move = choose_human_move(state, legal)
            if move is None:
                path = save_game(game, meta)
                print(f"\nGame stopped. Saved to {path}")
                return
        else:
            move = bot.choose(state, seat, legal)
            print(f"   {bot_name}: {describe(move, state)}")
            time.sleep(delay)
        game.play(move)
        seq = print_new_events(game.state, seq)

    print()
    show_board(game.state)
    if game.winner is None:
        print(f"\nNo winner after {game.turns} turns.")
    elif game.winner == human_seat:
        print(f"\n🏆 YOU WIN in {game.turns} turns!")
    else:
        print(f"\n🤖 {bot_name} wins in {game.turns} turns.")
    print(f"Game saved to {save_game(game, meta)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--opponent", default="simple", help="random or simple (default: simple)")
    ap.add_argument("--mode", choices=["basic", "harbour"], default="basic")
    ap.add_argument("--second", action="store_true", help="the bot takes the first turn")
    ap.add_argument("--name", default="You")
    ap.add_argument("--seed", type=int, help="fixed dice seed (default: random)")
    ap.add_argument("--delay", type=float, default=0.8, help="seconds to pause after each bot move")
    ap.add_argument("--replay", metavar="FILE", help="watch a saved game instead of playing")
    args = ap.parse_args(argv)

    if args.replay:
        replay(args.replay, args.delay)
        return
    seed = args.seed if args.seed is not None else random.randrange(1_000_000_000)
    try:
        play(args.opponent, args.mode, not args.second, args.delay, seed, args.name)
    except KeyboardInterrupt:
        print("\nBye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
