"""Stage 5 Phase C — training, checkpoints, TrainedBot, safe loading.

Fast checks only (a tiny training run); the real win-rate milestones are measured
with simulate.py and recorded in the learning journal. Needs `.venv-ai` with the
Phase C packages; skipped elsewhere.
"""
import pickle

import pytest

pytest.importorskip("torch")
pytest.importorskip("sb3_contrib")

import torch  # noqa: E402

from machi_koro_ai import trained_bot  # noqa: E402
from machi_koro_ai import train  # noqa: E402
from machi_koro_ai.bots import RandomBot, make_bot  # noqa: E402
from machi_koro_ai.game import play_game  # noqa: E402


@pytest.fixture
def checkpoints(tmp_path, monkeypatch):
    monkeypatch.setattr(trained_bot, "CHECKPOINTS", tmp_path)
    monkeypatch.setattr(train, "CHECKPOINTS", tmp_path)
    return tmp_path


def tiny_run(name, *extra):
    train.main(["--run", name, "--steps", "2048", "--envs", "2", "--threads", "1",
                "--save-every", "1024", "--eval-every", "100000", *extra])


def test_training_saves_a_brain_that_plays_only_legal_moves(checkpoints):
    tiny_run("tiny")
    assert (checkpoints / "tiny" / "latest" / "policy.pt").exists()
    assert (checkpoints / "tiny" / "step_1024" / "policy.pt").exists()
    ai = make_bot("trained:tiny")
    for g in range(20):                       # play_game raises on any illegal move
        game = play_game([ai, RandomBot(g)] if g % 2 else [RandomBot(g), ai], seed=g)
        assert game.winner is not None


def test_resume_continues_the_step_count(checkpoints):
    tiny_run("tiny")
    tiny_run("tiny", "--resume", "--steps", "4096")
    steps = sorted(int(p.name.split("_")[1]) for p in (checkpoints / "tiny").glob("step_*"))
    first_run = [s for s in steps if s <= 2048]
    assert first_run, steps            # the first run's saves are kept…
    assert steps[-1] >= 4096, steps    # …and the resumed run counted on from them


def test_refuses_to_overwrite_an_existing_run(checkpoints):
    tiny_run("tiny")
    with pytest.raises(SystemExit):
        tiny_run("tiny")


class Boom:
    """A pickle that would run code when loaded."""
    def __reduce__(self):
        return (print, ("this must never run",))


def test_brain_loader_rejects_files_that_are_not_plain_weights(checkpoints):
    """Plan S1: only plain tensors load; a pickled object is refused."""
    tiny_run("tiny")
    weights = checkpoints / "tiny" / "latest" / "policy.pt"
    torch.save({"evil": Boom()}, weights)
    with pytest.raises(pickle.UnpicklingError):
        make_bot("trained:tiny")
