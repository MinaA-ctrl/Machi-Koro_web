"""See a game position the way the AI sees it.

    cd websocket-server
    .venv-ai/bin/python -m machi_koro_ai.eyes              # a position after 10 turns
    .venv-ai/bin/python -m machi_koro_ai.eyes --turns 25 --all

Plays SimpleBot vs RandomBot up to the chosen turn, then prints the board the way
a person sees it, the same moment as the AI's row of numbers, and its menu with
the allowed moves.
"""
import argparse

from .bots import RandomBot, SimpleBot
from .encoding import Encoding
from .game import Game, make_config
from .play import show_board


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--all", action="store_true", help="also show the numbers that are 0")
    args = ap.parse_args(argv)

    config = make_config("basic")
    enc = Encoding(config, 2)
    bots = [SimpleBot(), RandomBot(args.seed)]
    game = Game(args.seed, ["Simple", "Random"], config=config)
    while not game.finished and not (game.turns >= args.turns and game.state["phase"] == "build"):
        seat = game.to_move
        game.play(bots[seat].choose(game.state, seat, game.legal_moves()))

    me = game.to_move
    print(f"\n── What a person sees (turn {game.turns}, {game.state['players'][me]['name']} to move) ──")
    show_board(game.state)

    obs = enc.observe(game.state, me)
    print(f"\n── What the AI sees: {len(obs)} numbers ──")
    print("[" + ", ".join(f"{v:.2f}".rstrip("0").rstrip(".") for v in obs) + "]")
    print("\nThe same numbers with labels" + ("" if args.all else " (zeros hidden)") + ":")
    for label, value in enc.describe_observation(obs):
        if value or args.all:
            print(f"   {value:6.2f}   {label}")

    mask = enc.mask(game.state, me)
    print(f"\n── The AI's menu: {enc.n_actions} moves, {int(mask.sum())} allowed right now ──")
    for i in range(enc.n_actions):
        if mask[i]:
            print(f"   #{i:<3} {enc.describe_action(i)}")
    print(f"   (the other {enc.n_actions - int(mask.sum())} are greyed out)")


if __name__ == "__main__":
    main()
