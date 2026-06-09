"""Shared fixtures for the engine characterization suite (TASK-005).

Two determinism techniques are used across the suite:

1. Direct `resolve_cards(state, roll)` calls — exact card-payout math with no
   dice at all. This is the cleanest way to lock in per-card amounts.
2. `force_rolls(...)` — monkeypatches `game_engine.roll_die` to yield a scripted
   sequence, for paths that go through `handle_action` (rolls, tuna, reroll).

The `seed()` seam (Backend's TASK-005 unblocker) is exercised directly in the
determinism tests; `force_rolls` is preferred elsewhere because it lets a test
pin an *exact* face rather than reverse-engineering a seed.
"""
import pytest
import machi_koro_engine.game_engine as ge


@pytest.fixture
def force_rolls(monkeypatch):
    """Return a callable that scripts the values `roll_die()` will yield, in order.

    Example: force_rolls(6, 6, 2, 5)  ->  first two roll_die() calls return 6,6;
    next two return 2,5. Raises StopIteration if the engine rolls more than scripted
    (which surfaces an unexpected extra roll as a test failure rather than a hang).
    """
    def _apply(*sequence):
        it = iter(sequence)
        monkeypatch.setattr(ge, "roll_die", lambda: next(it))
    return _apply
