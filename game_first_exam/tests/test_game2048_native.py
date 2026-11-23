"""Compare the adapter against direct pinned Gymnasium 2048 calls."""
import importlib.util
import sys
import unittest
from pathlib import Path

import gymnasium as gym
import gymnasium_2048  # noqa: F401 - registration
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'game_first_exam/runtime'))
spec = importlib.util.spec_from_file_location(
    'game2048_native_backend', ROOT / 'game_first_exam/benchmarks/game2048/adapter.py')
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


def config(seed=42):
    return {
        'engine_versions': {'gymnasium-2048': '0.1.2', 'gymnasium': '1.3.0',
                            'numpy': '1.26.4', 'pygame': '2.6.1'},
        'env_id': 'gymnasium_2048/TwentyFortyEight-v0', 'seed': seed,
        'board_size': 4, 'native_max_power': 16,
        'native_render_shape': [460, 400, 3], 'target_power': 11,
    }


def native_env(cfg):
    return gym.make(cfg['env_id'], render_mode='rgb_array', size=cfg['board_size'],
                    max_pow=cfg['native_max_power'])


def native_state(env):
    native = env.unwrapped
    return {
        'board': native.board.copy(),
        'rng': native.np_random.bit_generator.state,
        'step_score': native.step_score,
        'total_score': native.total_score,
        'is_legal': native.is_legal,
        'illegal_count': native.illegal_count,
    }


class Game2048NativeTests(unittest.TestCase):
    def assert_state_equal(self, left, right):
        np.testing.assert_array_equal(left.pop('board'), right.pop('board'))
        self.assertEqual(left, right)

    def test_all_actions_match_native_indices(self):
        cfg = config()
        for name, index in backend.ACTIONS.items():
            with self.subTest(action=name):
                adapter = backend.Adapter(cfg)
                raw = native_env(cfg)
                try:
                    observation, _ = raw.reset(seed=cfg['seed'])
                    np.testing.assert_array_equal(adapter.env.unwrapped._get_obs(), observation)
                    np.testing.assert_array_equal(adapter.frame(), raw.render())
                    observation, reward, terminated, truncated, _ = raw.step(index)
                    transition = adapter.step(name)
                    self.assertEqual((transition.reward, transition.terminated,
                                      transition.truncated),
                                     (float(reward), bool(terminated), bool(truncated)))
                    np.testing.assert_array_equal(adapter.frame(), raw.render())
                    np.testing.assert_array_equal(adapter.env.unwrapped._get_obs(), observation)
                    self.assert_state_equal(native_state(adapter.env), native_state(raw))
                finally:
                    adapter.close(); raw.close()

    def test_seeded_trajectory_matches_native(self):
        sequence = ['UP', 'RIGHT', 'DOWN', 'LEFT', 'LEFT', 'UP', 'RIGHT', 'DOWN']
        for seed in (0, 42, 123):
            with self.subTest(seed=seed):
                cfg = config(seed)
                adapter = backend.Adapter(cfg)
                raw = native_env(cfg)
                try:
                    observation, _ = raw.reset(seed=seed)
                    np.testing.assert_array_equal(adapter.env.unwrapped._get_obs(), observation)
                    initial = adapter.fingerprint()
                    adapter.spec(); adapter.observe(); adapter.metrics(); adapter.frame()
                    self.assertEqual(adapter.fingerprint(), initial)
                    for step in range(512):
                        name = sequence[step % len(sequence)]
                        observation, reward, terminated, truncated, _ = raw.step(
                            backend.ACTIONS[name])
                        transition = adapter.step(name)
                        self.assertEqual((transition.reward, transition.terminated,
                                          transition.truncated),
                                         (float(reward), bool(terminated), bool(truncated)))
                        np.testing.assert_array_equal(adapter.env.unwrapped._get_obs(), observation)
                        np.testing.assert_array_equal(adapter.frame(), raw.render())
                        self.assert_state_equal(native_state(adapter.env), native_state(raw))
                        if terminated or truncated:
                            break
                    else:
                        self.fail('native 2048 episode did not end within 512 actions')
                finally:
                    adapter.close(); raw.close()

    def test_seeded_initial_states_are_reproducible(self):
        first = backend.Adapter(config(42))
        second = backend.Adapter(config(42))
        other = backend.Adapter(config(43))
        try:
            self.assertEqual(first.fingerprint(), second.fingerprint())
            self.assertNotEqual(first.fingerprint(), other.fingerprint())
        finally:
            first.close(); second.close(); other.close()


if __name__ == '__main__':
    unittest.main()
