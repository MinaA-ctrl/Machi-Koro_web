"""A headless game: the engine state plus its own seeded dice.

    game = Game(seed=7, player_names=["You", "Bot"])
    while not game.finished:
        move = some_bot.choose(game.state, game.to_move, game.legal_moves())
        game.play(move)

Every move is recorded in `game.moves`, so (seed, config, names, moves) replays the
exact same game — that's how the text game saves and replays.
"""
import random

from machi_koro_engine import (
    create_initial_state, config_for, handle_action, legal_actions, use_rng,
)
from machi_koro_engine.game_config import build_config, CONFIGS

# A game that runs this many turns without a winner is stopped (counts as a draw).
MAX_TURNS = 500


class IllegalMove(Exception):
    pass


def make_config(mode="basic", sharp=False, variable_supply=None):
    """'basic' / 'harbour' (+ optional Sharp / Variable Supply) → GameConfig."""
    return build_config(CONFIGS[mode], sharp=sharp, variable_supply=variable_supply)


class Game:
    def __init__(self, seed, player_names, config=None, max_turns=MAX_TURNS):
        self.seed = seed
        self.config = config or config_for("basic")
        self.player_names = list(player_names)
        self.max_turns = max_turns
        self.rng = random.Random(seed)
        self.moves = []          # [(seat, move), ...] — everything needed to replay
        self.turns = 0           # number of dice rolls taken (one per turn)
        with use_rng(self.rng):
            self.state = create_initial_state(
                [{"seat": i, "display_name": n} for i, n in enumerate(self.player_names)],
                config=self.config,
            )

    @property
    def to_move(self):
        """The seat that must decide now (every decision belongs to the active player)."""
        return self.state["active_seat"]

    @property
    def finished(self):
        return self.state["phase"] == "finished" or self.turns >= self.max_turns

    @property
    def winner(self):
        """Winning seat, or None (game unfinished or stopped at the turn cap)."""
        return self.state.get("winner")

    def legal_moves(self):
        return legal_actions(self.state, self.to_move)

    def play(self, move):
        """Apply `move` for the player to move. Raises IllegalMove if the engine refuses it."""
        seat = self.to_move
        with use_rng(self.rng):
            result = handle_action(self.state, seat, move)
        if not result:
            raise IllegalMove(f"seat {seat} in phase {self.state['phase']}: {move}")
        self.moves.append((seat, move))
        if move.get("event") == "roll":
            self.turns += 1
        return result


def play_game(bots, seed, config=None, max_turns=MAX_TURNS):
    """Play one full game; bots[i] sits in seat i. Returns the finished Game."""
    game = Game(seed, [b.name for b in bots], config=config, max_turns=max_turns)
    while not game.finished:
        seat = game.to_move
        game.play(bots[seat].choose(game.state, seat, game.legal_moves()))
    return game
