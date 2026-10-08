"""Bot players. `make_bot(name, seed)` builds one by name:

    "random", "simple"           hand-written bots
    "trained:<run>[/step_N]"     a brain trained by train.py (needs .venv-ai)
"""
from .base import Bot
from .random_bot import RandomBot
from .simple_bot import SimpleBot

BOTS = {"random": RandomBot, "simple": SimpleBot}


def make_bot(name, seed=None):
    if name.lower().startswith("trained:"):
        from ..trained_bot import TrainedBot   # imports torch — only when asked for
        return TrainedBot(name.split(":", 1)[1])
    cls = BOTS[name.lower()]
    return cls(seed) if cls is RandomBot else cls()


__all__ = ["Bot", "RandomBot", "SimpleBot", "BOTS", "make_bot"]
