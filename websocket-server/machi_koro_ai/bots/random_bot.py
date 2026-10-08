import random

from .base import Bot


class RandomBot(Bot):
    """Picks any legal move at random — the weakest possible player, used as a
    baseline. Has its own RNG so it never disturbs the game's dice."""
    name = "Random"

    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def choose(self, state, seat, legal_moves):
        return self.rng.choice(legal_moves)
