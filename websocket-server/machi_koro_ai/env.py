"""Machi Koro as a Gymnasium environment — the standard "game box" AI tools plug into.

The learning agent plays one seat; bots play the others inside `step()`, so from
the agent's point of view each step is: I act → opponents act → my next decision.

    env = MachiKoroEnv(opponents=["random"])
    obs, info = env.reset(seed=0)
    while True:
        action = pick_from(info["action_mask"])
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            break

Reward: +1 for a win, −1 for a loss, 0 if the game hits the turn cap. Optionally
a small bonus per landmark the agent builds (`landmark_bonus`, off by default) —
kept so we can compare learning with and without it.
"""
import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .bots import make_bot
from .encoding import OBS_HIGH, Encoding
from .game import MAX_TURNS, Game, make_config


class MachiKoroEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, opponents=("random",), mode="basic", landmark_bonus=0.0,
                 max_turns=MAX_TURNS, illegal_action="raise"):
        """`opponents`: one bot name per other seat ("random", "simple").
        `illegal_action`: "raise" (default — a masked agent never picks one, so it's
        a bug) or "lose" (end the episode as a loss; for tools that ignore masks)."""
        self.opponent_names = list(opponents)
        self.n_players = 1 + len(self.opponent_names)
        self.config = make_config(mode)
        self.enc = Encoding(self.config, self.n_players)
        self.landmark_bonus = landmark_bonus
        self.max_turns = max_turns
        self.illegal_action = illegal_action
        self.observation_space = spaces.Box(0.0, OBS_HIGH, (self.enc.obs_size,), np.float32)
        self.action_space = spaces.Discrete(self.enc.n_actions)
        self.game = None

    # ── gymnasium API ─────────────────────────────────────────────────────────

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        rng = self.np_random
        self.me = int(rng.integers(self.n_players))       # learn from every seat
        others = [s for s in range(self.n_players) if s != self.me]
        self.bots = {seat: make_bot(name, seed=int(rng.integers(2**31)))
                     for seat, name in zip(others, self.opponent_names)}
        names = ["Agent" if s == self.me else self.bots[s].name for s in range(self.n_players)]
        self.game = Game(int(rng.integers(2**31)), names, config=self.config,
                         max_turns=self.max_turns)
        self._play_opponents()
        return self._obs(), self._info()

    def step(self, action):
        state = self.game.state
        legal = self.game.legal_moves()
        move = self.enc.action_to_move(int(action), state, self.me)
        if move not in legal:
            if self.illegal_action == "raise":
                raise ValueError(f"illegal action {action} ({self.enc.describe_action(action)})")
            return self._obs(), -1.0, True, False, self._info()

        before = self._my_landmarks()
        self.game.play(move)
        self._play_opponents()

        reward = self.landmark_bonus * (self._my_landmarks() - before)
        terminated = self.game.state["phase"] == "finished"
        truncated = not terminated and self.game.finished       # hit the turn cap
        if terminated:
            reward += 1.0 if self.game.winner == self.me else -1.0
        return self._obs(), reward, terminated, truncated, self._info()

    def action_masks(self):
        """Allowed menu items now (the name sb3-contrib's MaskablePPO looks for)."""
        if self.game.finished:
            return np.zeros(self.enc.n_actions, dtype=bool)
        return self.enc.mask(self.game.state, self.me)

    # ── internals ─────────────────────────────────────────────────────────────

    def _play_opponents(self):
        while not self.game.finished and self.game.to_move != self.me:
            seat = self.game.to_move
            self.game.play(self.bots[seat].choose(self.game.state, seat, self.game.legal_moves()))

    def _my_landmarks(self):
        me = next(p for p in self.game.state["players"] if p["seat"] == self.me)
        return sum(lm["built"] for lm in me["landmarks"])

    def _obs(self):
        return self.enc.observe(self.game.state, self.me)

    def _info(self):
        return {"action_mask": self.action_masks(), "seat": self.me, "turns": self.game.turns}
