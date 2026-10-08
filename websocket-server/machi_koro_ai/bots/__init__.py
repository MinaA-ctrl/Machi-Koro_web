"""Bot players. `make_bot("random" | "simple", seed)` builds one by name."""
from .base import Bot
from .random_bot import RandomBot
from .simple_bot import SimpleBot

BOTS = {"random": RandomBot, "simple": SimpleBot}


def make_bot(name, seed=None):
    cls = BOTS[name.lower()]
    return cls(seed) if cls is RandomBot else cls()


__all__ = ["Bot", "RandomBot", "SimpleBot", "BOTS", "make_bot"]
