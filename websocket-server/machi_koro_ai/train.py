"""Train a Machi Koro brain with PPO (MaskablePPO from sb3-contrib).

    cd websocket-server
    # 1. learn the basics against RandomBot
    .venv-ai/bin/python -m machi_koro_ai.train --run first --opponent random --steps 300000
    # 2. keep going against SimpleBot, starting from that brain
    .venv-ai/bin/python -m machi_koro_ai.train --run second --init-from first --opponent simple --steps 1000000
    # stopped it (Ctrl+C)? continue where it left off:
    .venv-ai/bin/python -m machi_koro_ai.train --run second --resume --opponent simple --steps 1000000

    # watch the live charts (in another terminal), then open http://localhost:6006
    .venv-ai/bin/tensorboard --logdir machi_koro_ai/checkpoints

Everything for a run lives in machi_koro_ai/checkpoints/<run>/ (gitignored):
  latest/ and step_<N>/  — the brain (policy.pt + brain.json) for TrainedBot
  ppo_latest.zip          — full trainer state, used only by --resume / --init-from
  tb/                     — chart data for TensorBoard
"""
import argparse
import time
from collections import deque
from pathlib import Path

import numpy as np
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

from .bots import SimpleBot
from .env import MachiKoroEnv
from .game import Game, make_config
from .trained_bot import CHECKPOINTS, save_brain

NET_ARCH = [128, 128]


def make_env(opponent, mode, seed):
    def _init():
        env = MachiKoroEnv(opponents=[opponent], mode=mode)
        env.reset(seed=seed)
        return Monitor(env)
    return _init


def evaluate_vs_simple(policy, enc, games, seed=10_000):
    """Win rate of `policy` (best move, no randomness) against SimpleBot."""
    wins = 0
    for g in range(games):
        me = g % 2                                         # alternate who starts
        game = Game(seed + g, ["AI", "Simple"] if me == 0 else ["Simple", "AI"])
        simple = SimpleBot()
        while not game.finished:
            seat, legal = game.to_move, game.legal_moves()
            if seat == me:
                obs, mask = enc.observe(game.state, seat), enc.mask(game.state, seat, legal)
                action, _ = policy.predict(obs, action_masks=mask, deterministic=True)
                move = enc.action_to_move(int(action), game.state, seat)
            else:
                move = simple.choose(game.state, seat, legal)
            game.play(move)
        wins += game.winner == me
    return wins / games


class Progress(BaseCallback):
    """Logs the win rate to the charts, prints progress, saves checkpoints and runs
    the SimpleBot exam every `eval_every` steps."""

    def __init__(self, run_dir, meta, save_every, eval_every, eval_games):
        super().__init__()
        self.run_dir, self.meta = Path(run_dir), meta
        self.save_every, self.eval_every, self.eval_games = save_every, eval_every, eval_games
        self.results = deque(maxlen=500)       # last 500 training games: 1 = win
        self.start = time.time()
        self.next_save = self.next_eval = 0

    def _on_training_start(self):
        now = self.num_timesteps
        self.next_save = now + self.save_every
        self.next_eval = now + self.eval_every
        self.start_steps = now

    def _on_step(self):
        for info in self.locals["infos"]:
            if "episode" in info:
                self.results.append(1.0 if info["episode"]["r"] > 0 else 0.0)
        if self.num_timesteps >= self.next_eval:
            self.next_eval += self.eval_every
            enc = self.training_env.envs[0].unwrapped.enc
            rate = evaluate_vs_simple(self.model.policy, enc, self.eval_games)
            self.logger.record("exam/win_rate_vs_simple", rate)
            print(f"   📝 exam: {100 * rate:.1f}% wins vs SimpleBot ({self.eval_games} games)")
        if self.num_timesteps >= self.next_save:
            self.next_save += self.save_every
            self.save(f"step_{self.num_timesteps}")
        return True

    def _on_rollout_end(self):
        if self.results:
            rate = float(np.mean(self.results))
            self.logger.record("game/win_rate_training", rate)
            done = self.num_timesteps - self.start_steps
            speed = done / max(time.time() - self.start, 1e-9)
            print(f"step {self.num_timesteps:>9,}  win rate (last {len(self.results)} games): "
                  f"{100 * rate:5.1f}%   {speed:,.0f} steps/sec")

    def save(self, name):
        save_brain(self.model.policy, self.run_dir / name, self.meta)
        save_brain(self.model.policy, self.run_dir / "latest", self.meta)
        self.model.save(self.run_dir / "ppo_latest.zip")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="name for this training run")
    ap.add_argument("--opponent", default="random", choices=["random", "simple"])
    ap.add_argument("--steps", type=int, default=300_000, help="total AI decisions to train on")
    ap.add_argument("--mode", default="basic", choices=["basic"])
    ap.add_argument("--threads", type=int, default=2, help="CPU cores to use (default 2)")
    ap.add_argument("--envs", type=int, default=8, help="games played side by side")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--resume", action="store_true", help="continue this run from its last save")
    ap.add_argument("--init-from", metavar="RUN", help="start from another run's brain")
    ap.add_argument("--save-every", type=int, default=50_000)
    ap.add_argument("--eval-every", type=int, default=50_000)
    ap.add_argument("--eval-games", type=int, default=200)
    args = ap.parse_args(argv)

    torch.set_num_threads(args.threads)
    run_dir = CHECKPOINTS / args.run
    env = DummyVecEnv([make_env(args.opponent, args.mode, args.seed * 1000 + i) for i in range(args.envs)])
    enc = env.envs[0].unwrapped.enc
    meta = {"mode": args.mode, "n_players": 2, "obs_size": enc.obs_size,
            "n_actions": enc.n_actions, "net_arch": NET_ARCH}

    if args.resume or args.init_from:
        source = run_dir if args.resume else CHECKPOINTS / args.init_from
        print(f"Loading trainer from {source / 'ppo_latest.zip'}")
        model = MaskablePPO.load(source / "ppo_latest.zip", env=env, device="cpu",
                                 tensorboard_log=str(run_dir / "tb"))
    else:
        if (run_dir / "ppo_latest.zip").exists():
            raise SystemExit(f"Run '{args.run}' already exists — use --resume or a new --run name.")
        model = MaskablePPO(
            "MlpPolicy", env, device="cpu", seed=args.seed,
            n_steps=512, batch_size=512, n_epochs=5,
            gamma=0.995, gae_lambda=0.95, learning_rate=3e-4, ent_coef=0.01,
            policy_kwargs={"net_arch": NET_ARCH},
            tensorboard_log=str(run_dir / "tb"),
        )

    remaining = args.steps - (model.num_timesteps if args.resume else 0)
    if remaining <= 0:
        print(f"Run '{args.run}' already trained {model.num_timesteps:,} steps.")
        return
    print(f"Training '{args.run}' vs {args.opponent} for {remaining:,} steps "
          f"on {args.threads} CPU thread(s). Ctrl+C stops safely (progress is saved).")
    progress = Progress(run_dir, meta, args.save_every, args.eval_every, args.eval_games)
    try:
        model.learn(remaining, callback=progress, reset_num_timesteps=not args.resume,
                    tb_log_name="ppo")
    except KeyboardInterrupt:
        print("\nStopped by you.")
    progress.save(f"step_{model.num_timesteps}")
    print(f"Saved. Brain: {run_dir / 'latest'}   (try it: --opponent trained:{args.run})")


if __name__ == "__main__":
    main()
