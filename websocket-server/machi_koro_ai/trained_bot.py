"""TrainedBot — plays with a brain saved by train.py.

Loads ONLY plain network weights (`policy.pt`, read with torch's weights_only
mode) plus a small JSON description — never a pickled object, because pickled
files can run code when opened (plan S1). Only load checkpoints you trained.

    make_bot("trained:first")             # latest brain of run "first"
    make_bot("trained:first/step_200000") # a specific checkpoint
"""
import json
from pathlib import Path

import numpy as np
import torch
from gymnasium import spaces
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy

from .bots.base import Bot
from .encoding import OBS_HIGH, Encoding
from .game import make_config

CHECKPOINTS = Path(__file__).parent / "checkpoints"


def save_brain(policy, folder, meta):
    """Write policy weights + description to `folder` (policy.pt, brain.json)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    torch.save(policy.state_dict(), folder / "policy.pt")
    (folder / "brain.json").write_text(json.dumps(meta, indent=1))


def resolve(ref):
    """'first' → checkpoints/first/latest ; 'first/step_200000' → that folder."""
    path = CHECKPOINTS / ref
    if (path / "latest" / "policy.pt").exists():
        path = path / "latest"
    if not (path / "policy.pt").exists():
        raise FileNotFoundError(f"no trained brain at {path}")
    return path


def load_policy(folder):
    folder = Path(folder)
    meta = json.loads((folder / "brain.json").read_text())
    enc = Encoding(make_config(meta["mode"]), meta["n_players"])
    if (enc.obs_size, enc.n_actions) != (meta["obs_size"], meta["n_actions"]):
        raise ValueError(f"{folder}: brain was trained for a different game encoding")
    policy = MaskableActorCriticPolicy(
        spaces.Box(0.0, OBS_HIGH, (enc.obs_size,), np.float32),
        spaces.Discrete(enc.n_actions),
        lr_schedule=lambda _: 0.0,
        net_arch=meta["net_arch"],
    )
    weights = torch.load(folder / "policy.pt", map_location="cpu", weights_only=True)
    policy.load_state_dict(weights)
    policy.eval()
    return policy, enc, meta


class TrainedBot(Bot):
    def __init__(self, ref, deterministic=True):
        torch.set_num_threads(1)
        self.policy, self.enc, self.meta = load_policy(resolve(ref))
        self.deterministic = deterministic
        self.name = f"AI[{ref}]"

    def choose(self, state, seat, legal_moves):
        obs = self.enc.observe(state, seat)
        mask = self.enc.mask(state, seat, legal_moves)
        action, _ = self.policy.predict(obs, action_masks=mask, deterministic=self.deterministic)
        return self.enc.action_to_move(int(action), state, seat)
