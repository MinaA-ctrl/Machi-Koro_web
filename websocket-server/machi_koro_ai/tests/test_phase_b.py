"""Stage 5 Phase B — the game as numbers: observation, action menu, mask, env.

Each test maps to a row of Phase B's "Done when" table in
`Developer stages/stage-5-ai-plan.md`. Needs the AI environment
(`.venv-ai`, see requirements-ai.txt); skipped elsewhere.
"""
import random

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("gymnasium")

from gymnasium.utils.env_checker import check_env  # noqa: E402

from machi_koro_ai.bots import RandomBot  # noqa: E402
from machi_koro_ai.encoding import OBS_HIGH, Encoding  # noqa: E402
from machi_koro_ai.env import MachiKoroEnv  # noqa: E402
from machi_koro_ai.game import Game, make_config  # noqa: E402

MODES = ["basic", "harbour"]


def decisions(games, seed=0):
    """Yield (encoding, state, seat, legal) at every decision of random games in
    Basic and Harbour with 2–4 players."""
    rng = random.Random(seed)
    for g in range(games):
        mode, n = MODES[g % 2], 2 + g % 3
        config = make_config(mode)
        enc = Encoding(config, n)
        bots = [RandomBot(rng.random()) for _ in range(n)]
        game = Game(g, [b.name for b in bots], config=config)
        while not game.finished:
            seat, legal = game.to_move, game.legal_moves()
            yield enc, game.state, seat, legal
            game.play(bots[seat].choose(game.state, seat, legal))


def test_round_trip_move_to_number_and_back():
    for enc, state, seat, legal in decisions(1000):
        for move in legal:
            assert enc.action_to_move(enc.move_to_action(move, state, seat), state, seat) == move


def test_mask_marks_exactly_the_legal_moves():
    for enc, state, seat, legal in decisions(1000, seed=1):
        allowed = [enc.action_to_move(a, state, seat) for a in np.flatnonzero(enc.mask(state, seat))]
        assert sorted(map(str, allowed)) == sorted(map(str, legal))


def test_observation_has_fixed_size_and_sane_values():
    for enc, state, seat, legal in decisions(300, seed=2):
        obs = enc.observe(state, seat)
        assert obs.shape == (enc.obs_size,) and obs.dtype == np.float32
        assert np.isfinite(obs).all() and (obs >= 0).all() and (obs <= OBS_HIGH).all()
    assert len(enc.describe_observation(obs)) == enc.obs_size


def test_hidden_deck_order_is_not_visible():
    """Plan S2: two states differing only in the face-down deck look identical."""
    config = make_config("basic", variable_supply=True)
    enc = Encoding(config, 2)
    state = Game(5, ["A", "B"], config=config).state
    shuffled = {**state, "deck": list(reversed(state["deck"]))}
    assert state["deck"] != shuffled["deck"]
    assert (enc.observe(state, 0) == enc.observe(shuffled, 0)).all()


def test_gymnasium_check_env_passes():
    check_env(MachiKoroEnv(opponents=["random"], illegal_action="lose"), skip_render_check=True)


def play_random_episode(env, seed, rng):
    obs, info = env.reset(seed=seed)
    rewards = []
    while True:
        action = rng.choice(np.flatnonzero(info["action_mask"]))
        obs, reward, terminated, truncated, info = env.step(action)
        rewards.append(reward)
        if terminated or truncated:
            return rewards, env


def test_random_agent_matches_phase_a_random_win_rate():
    env, rng = MachiKoroEnv(opponents=["random"]), np.random.default_rng(0)
    wins = sum(play_random_episode(env, g, rng)[0][-1] > 0 for g in range(1000))
    assert 450 <= wins <= 550, wins


def test_rewards_are_win_plus_one_loss_minus_one_nothing_else():
    env, rng = MachiKoroEnv(opponents=["simple"]), np.random.default_rng(1)
    outcomes = set()
    for g in range(200):
        rewards, env = play_random_episode(env, g, rng)
        assert all(r == 0 for r in rewards[:-1])
        assert rewards[-1] == (1.0 if env.game.winner == env.me else -1.0)
        outcomes.add(rewards[-1])
    assert outcomes == {1.0, -1.0}


def test_landmark_bonus_only_when_switched_on():
    env, rng = MachiKoroEnv(opponents=["random"], landmark_bonus=0.1), np.random.default_rng(2)
    rewards, env = play_random_episode(env, 3, rng)
    me = next(p for p in env.game.state["players"] if p["seat"] == env.me)
    built = sum(lm["built"] for lm in me["landmarks"])
    final = 1.0 if env.game.winner == env.me else -1.0
    assert sum(rewards) == pytest.approx(0.1 * built + final)


def test_masked_agent_never_hits_an_illegal_action_and_unmasked_one_is_refused():
    env = MachiKoroEnv(opponents=["random"])
    obs, info = env.reset(seed=0)
    illegal = int(np.flatnonzero(~info["action_mask"])[0])
    with pytest.raises(ValueError):
        env.step(illegal)
