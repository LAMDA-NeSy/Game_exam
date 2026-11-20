"""Compare the adapter against real Tetris Gymnasium native calls."""
import importlib.util
import sys
import unittest
from pathlib import Path

import gymnasium as gym
import numpy as np
from tetris_gymnasium.envs import Tetris as _Tetris  # noqa: F401 - registration
from tetris_gymnasium.wrappers.observation import RgbObservation

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'game_first_exam/runtime'))
spec = importlib.util.spec_from_file_location(
    'tetris_native_backend', ROOT / 'game_first_exam/benchmarks/tetris/adapter.py')
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


def config(seed=42):
    return {
        'engine_versions': {'tetris-gymnasium': '0.2.1', 'gymnasium': '1.4.0',
                            'numpy': '1.26.4', 'opencv-python': '4.10.0.84'},
        'env_id': 'tetris_gymnasium/Tetris', 'seed': seed,
        'board_width': 10, 'board_height': 20, 'gravity': True,
        'native_queue_size': 4, 'native_holder_size': 1, 'target_lines': 1,
    }


def native_env(cfg):
    env = gym.make(cfg['env_id'], render_mode='rgb_array', width=cfg['board_width'],
                   height=cfg['board_height'], gravity=cfg['gravity'])
    return RgbObservation(env)


def native_state(env):
    native = env.unwrapped
    return {
        'board': native.board.copy(), 'active': native.active_tetromino.matrix.copy(),
        'active_id': native.active_tetromino.id, 'x': native.x, 'y': native.y,
        'queue': list(native.queue.queue),
        'holder': [piece.id for piece in native.holder.queue],
        'bag': native.randomizer.bag.copy(), 'bag_index': native.randomizer.index,
        'rng': native.randomizer.rng.bit_generator.state,
        'has_swapped': native.has_swapped, 'game_over': native.game_over,
    }


class TetrisNativeTests(unittest.TestCase):
    def assert_state_equal(self, left, right):
        for key in ('board', 'active', 'bag'):
            np.testing.assert_array_equal(left.pop(key), right.pop(key))
        self.assertEqual(left, right)

    def test_all_actions_match_native_indices(self):
        cfg = config()
        for name, index in backend.ACTIONS.items():
            with self.subTest(action=name):
                adapter = backend.Adapter(cfg)
                raw = native_env(cfg)
                try:
                    observation, _ = raw.reset(seed=cfg['seed'])
                    np.testing.assert_array_equal(adapter.frame(), observation)
                    observation, reward, terminated, truncated, info = raw.step(index)
                    transition = adapter.step(name)
                    self.assertEqual((transition.reward, transition.terminated,
                                      transition.truncated),
                                     (float(reward), bool(terminated), bool(truncated)))
                    np.testing.assert_array_equal(adapter.frame(), observation)
                    self.assert_state_equal(native_state(adapter.env), native_state(raw))
                    self.assertEqual(adapter.metrics()['lines_cleared'], info['lines_cleared'])
                finally:
                    adapter.close()
                    raw.close()

    def test_seeded_trajectory_observation_reward_and_end_match(self):
        sequence = ['MOVE_LEFT', 'ROTATE_CLOCKWISE', 'MOVE_RIGHT', 'HARD_DROP',
                    'SWAP', 'MOVE_DOWN', 'ROTATE_COUNTERCLOCKWISE', 'HARD_DROP']
        for seed in (1, 42, 123):
            with self.subTest(seed=seed):
                cfg = config(seed)
                adapter = backend.Adapter(cfg)
                raw = native_env(cfg)
                total_lines = 0
                try:
                    observation, _ = raw.reset(seed=seed)
                    np.testing.assert_array_equal(adapter.frame(), observation)
                    initial = adapter.fingerprint()
                    adapter.spec(); adapter.observe(); adapter.metrics(); adapter.frame()
                    self.assertEqual(adapter.fingerprint(), initial)
                    for step in range(300):
                        name = sequence[step % len(sequence)]
                        observation, reward, terminated, truncated, info = raw.step(
                            backend.ACTIONS[name])
                        transition = adapter.step(name)
                        total_lines += info['lines_cleared']
                        self.assertEqual((transition.reward, transition.terminated,
                                          transition.truncated),
                                         (float(reward), bool(terminated), bool(truncated)))
                        np.testing.assert_array_equal(adapter.frame(), observation)
                        self.assert_state_equal(native_state(adapter.env), native_state(raw))
                        self.assertEqual(adapter.metrics()['lines_cleared'], total_lines)
                        if terminated or truncated:
                            self.assertTrue(terminated)
                            self.assertFalse(truncated)
                            break
                    else:
                        self.fail('native Tetris episode did not end within 300 actions')
                finally:
                    adapter.close()
                    raw.close()

    def test_positive_seeds_are_reproducible(self):
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
