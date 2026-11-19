"""Compare the adapter against real Procgen. Missing native packages fail loudly."""
import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np
from procgen import ProcgenGym3Env

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'game_first_exam/runtime'))
spec = importlib.util.spec_from_file_location('coinrun_native_backend',
    ROOT / 'game_first_exam/benchmarks/coinrun/adapter.py')
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


class CoinRunNativeTests(unittest.TestCase):
    def test_all_actions_match_native_key_combinations(self):
        config = {'engine_versions': {'procgen': '0.10.7', 'gym3': '0.3.3',
                                      'numpy': '1.26.4'},
                  'seed': 7, 'distribution_mode': 'easy'}
        adapter = backend.Adapter(config)
        native = ProcgenGym3Env(num=1, env_name='coinrun', num_levels=1,
            start_level=7, rand_seed=7, num_threads=1, distribution_mode='easy',
            use_sequential_levels=False, paint_vel_info=False)
        try:
            native.observe()
            expected = tuple('_'.join(combo) if combo else 'NOOP'
                             for combo in native.get_combos())
            self.assertEqual(backend.ACTIONS, expected)
            seen = set()
            for index in list(range(len(expected))) * 5:
                native.act(np.array([index], dtype=np.int32))
                rewards, observations, first = native.observe()
                transition = adapter.step(expected[index])
                seen.add(index)
                self.assertEqual(transition.reward, float(rewards[0]))
                self.assertEqual(transition.terminated, bool(first[0]))
                self.assertFalse(transition.truncated)
                self.assertEqual(adapter.env.get_state(), native.get_state())
                if first[0]:
                    break
                np.testing.assert_array_equal(adapter.frame(), observations['rgb'][0])
            self.assertEqual(seen, set(range(15)))
        finally:
            adapter.close()
            native.close()

    def test_native_timeout_is_preserved(self):
        adapter = backend.Adapter({'engine_versions': {'procgen': '0.10.7', 'gym3': '0.3.3',
            'numpy': '1.26.4'}, 'seed': 7, 'distribution_mode': 'easy'})
        try:
            for step in range(1000):
                transition = adapter.step('NOOP')
                self.assertEqual(transition.terminated, step == 999)
                self.assertFalse(transition.truncated)
            self.assertFalse(adapter.success())
            self.assertEqual(adapter.metrics()['native_steps'], 1000)
            self.assertEqual(adapter.metrics()['native_return'], 0)
        finally:
            adapter.close()

    def test_native_equivalence_and_first_episode_boundary(self):
        for mode in ('easy', 'hard'):
            for seed in (0, 1, 42):
                with self.subTest(mode=mode, seed=seed):
                    config = {'engine_versions': {'procgen': '0.10.7', 'gym3': '0.3.3',
                                                  'numpy': '1.26.4'},
                              'seed': seed, 'distribution_mode': mode}
                    adapter = backend.Adapter(config)
                    native = ProcgenGym3Env(num=1, env_name='coinrun', num_levels=1,
                        start_level=seed, rand_seed=seed, num_threads=1,
                        distribution_mode=mode, use_sequential_levels=False, paint_vel_info=False)
                    try:
                        _, observations, _ = native.observe()
                        np.testing.assert_array_equal(adapter.frame(), observations['rgb'][0])
                        self.assertEqual(adapter.env.get_state(), native.get_state())
                        initial_hash = adapter.fingerprint()
                        adapter.spec()
                        adapter.observe()
                        adapter.metrics()
                        self.assertEqual(adapter.fingerprint(), initial_hash)
                        for step in range(2000):
                            previous = adapter.frame()
                            index = 8 if step % 20 < 10 else 7
                            native.act(np.array([index], dtype=np.int32))
                            rewards, observations, first = native.observe()
                            transition = adapter.step(backend.ACTIONS[index])
                            self.assertEqual(transition.reward, float(rewards[0]))
                            self.assertEqual(transition.terminated, bool(first[0]))
                            self.assertEqual(adapter.env.get_state(), native.get_state())
                            if first[0]:
                                self.assertEqual(adapter.success(), bool(native.get_info()[0]['prev_level_complete']))
                                np.testing.assert_array_equal(adapter.frame(), previous)
                                with self.assertRaises(ValueError):
                                    adapter.step('NOOP')
                                break
                            np.testing.assert_array_equal(adapter.frame(), observations['rgb'][0])
                        else:
                            self.fail('native episode did not end within 2000 actions')
                    finally:
                        adapter.close()
                        native.close()


if __name__ == '__main__':
    unittest.main()
