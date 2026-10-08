"""Bot-vs-bot tournaments: win rates, game length, speed.

    cd websocket-server
    python3 -m machi_koro_ai.simulate simple random --games 1000
    python3 -m machi_koro_ai.simulate simple simple random --games 500 --mode harbour

Seats rotate every game so no bot always goes first, and each game uses a fixed
seed (seed, seed+1, …), so the same command always gives the same result.
"""
import argparse
import time
from collections import Counter

from .bots import make_bot
from .game import make_config, play_game


def run_match(bot_names, games, seed=0, config=None):
    """Play `games` games; returns a summary dict with wins per bot name."""
    config = config or make_config("basic")
    n = len(bot_names)
    wins = Counter()
    draws = 0
    turns = []
    start = time.perf_counter()
    for g in range(games):
        shift = g % n                              # rotate who sits first
        names = bot_names[shift:] + bot_names[:shift]
        bots = [make_bot(name, seed=seed * 1_000_003 + g * n + i) for i, name in enumerate(names)]
        game = play_game(bots, seed=seed * 1_000_003 + g, config=config)
        turns.append(game.turns)
        if game.winner is None:
            draws += 1
        else:
            wins[(names[game.winner], game.winner)] += 1
    elapsed = time.perf_counter() - start
    by_bot = Counter()
    for (name, _seat), w in wins.items():
        by_bot[name] += w
    return {
        "games": games,
        "wins": dict(by_bot),
        "draws": draws,
        "avg_turns": sum(turns) / games,
        "max_turns": max(turns),
        "games_per_sec": games / elapsed,
        "seconds": elapsed,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bots", nargs="+", help="2–5 bot names: random, simple")
    ap.add_argument("--games", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--mode", choices=["basic", "harbour"], default="basic")
    ap.add_argument("--sharp", action="store_true")
    args = ap.parse_args(argv)

    config = make_config(args.mode, sharp=args.sharp)
    r = run_match(args.bots, args.games, seed=args.seed, config=config)
    print(f"{r['games']} games of {config.name}, {len(args.bots)} players "
          f"({r['seconds']:.1f}s, {r['games_per_sec']:.0f} games/sec)")
    seats_per_name = Counter(args.bots)
    for name in dict.fromkeys(args.bots):
        w = r["wins"].get(name, 0)
        # With duplicates (e.g. simple simple random) report the per-seat average.
        print(f"  {name:<8} won {w:>5}  ({100 * w / r['games']:.1f}%"
              + (f", {100 * w / r['games'] / seats_per_name[name]:.1f}% per seat" if seats_per_name[name] > 1 else "")
              + ")")
    if r["draws"]:
        print(f"  unfinished (hit the turn cap): {r['draws']}")
    print(f"  average game: {r['avg_turns']:.1f} turns (longest {r['max_turns']})")


if __name__ == "__main__":
    main()
