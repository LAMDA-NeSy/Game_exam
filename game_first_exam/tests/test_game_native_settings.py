"""Check thin adapters against direct calls to the pinned native engines."""
import base64
import io
import json
import os
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'game_first_exam/tests'), str(ROOT/'game_first_exam/runtime')]
from test_game_adapters import module

BENCHMARK = os.environ['GAME_TEST_BENCHMARK']


class NativeSettings(unittest.TestCase):
    def test_native_defaults_observations_and_transitions(self):
        m = module('thin_adapter', ROOT/f'game_first_exam/benchmarks/{BENCHMARK}/adapter.py')
        tasks = [p for p in sorted((ROOT/'game_first_exam/tasks'/BENCHMARK).glob('*-standard')) if '-i00-' not in p.name]
        for task in tasks:
            cfg = json.loads((task/'tests/instance.json').read_text())
            with self.subTest(task=task.name):
                a = m.Adapter(cfg, task/'environment/sim')
                raw = None
                try:
                    if BENCHMARK == 'minigrid':
                        raw = m.gym.make(cfg['env_id'], render_mode='rgb_array')
                        obs, _ = raw.reset(seed=cfg['seed'])
                        self.assertEqual(raw.unwrapped.max_steps, cfg['native_max_steps'])
                        self.assertEqual(a.env.unwrapped.max_steps, raw.unwrapped.max_steps)
                        actions = json.loads((task/'solution/actions.json').read_text())
                        self.check_minigrid(a.observe(), obs)
                        for action in actions:
                            obs, reward, terminated, truncated, _ = raw.step(m.ACTIONS[action])
                            transition = a.step(action)
                            self.assertEqual((transition.reward, transition.terminated, transition.truncated), (reward, terminated, truncated))
                            self.check_minigrid(a.observe(), obs)
                            np.testing.assert_array_equal(a.env.unwrapped.grid.encode(), raw.unwrapped.grid.encode())
                            if terminated or truncated: break
                    elif BENCHMARK == 'crafter':
                        self.assertIs(type(a.env), m.crafter.Env)  # No subclass changes native dynamics.
                        raw = m.crafter.Env(seed=cfg['seed']); obs = raw.reset()
                        self.assertEqual((raw._length, a.env._length), (10000, 10000))
                        self.check_pixels(a.observe(), obs)
                        # Native set iteration can diverge at creature balancing (every 10 steps).
                        # Preserve that upstream behavior; do not claim cross-process trajectory identity.
                        for action in json.loads((task/'solution/actions.json').read_text())[:9]:
                            obs, reward, done, _ = raw.step(raw.action_names.index(action))
                            transition = a.step(action)
                            self.assertEqual(transition.reward, reward)
                            self.assertEqual(transition.terminated or transition.truncated, done)
                            self.check_pixels(a.observe(), obs)
                    elif BENCHMARK == 'textworld':
                        raw = m.textworld.start(str(task/'environment/sim/game.z8'), m.textworld.EnvInfos(
                            description=True, inventory=True, objective=True, score=True, max_score=True,
                            won=True, lost=True, moves=True))
                        raw.seed(cfg['seed']); state = raw.reset(); score = 0
                        import re
                        for action in ['look', 'i', 'xyzzy', 'LOOK']:
                            self.assertIsNotNone(re.fullmatch(a.spec()['action_schema']['pattern'], action))
                            state, total, done = raw.step(action); transition = a.step(action)
                            self.assertEqual(transition.reward, total-score); score = total
                            self.assertEqual(transition.terminated, done)
                            self.assertEqual(a.observe(), {k: state.get(k) or '' for k in ('feedback', 'description', 'inventory', 'objective')})
                        for command in ['restart', 'undo', 'save game', 'look\nlook', 'look.then look', 'tw-print-state', 'quit', 'q', 'g', 'noscript', ' q ', '\tG', ' noscript', 'print_state', 'enable print state option',
                                        'ENABLE  PRINT   STATE OPTION', 'disable print state option',
                                        'restrict commands', 'look then north']:
                            self.assertIsNone(re.fullmatch(a.spec()['action_schema']['pattern'], command))
                    else:
                        raw = m.baba.make(cfg['env_id']); raw.reset(seed=cfg['seed'])
                        self.assertEqual((raw.max_steps, a.env.max_steps), (100, 100))
                        self.check_pixels(a.observe(), raw.render(mode='rgb_array', tile_size=32))
                finally:
                    a.close()
                    if raw is not None and hasattr(raw, 'close'): raw.close()

    def check_pixels(self, observation, pixels):
        self.assertEqual(set(observation), {'image_png_base64'})
        decoded = np.asarray(Image.open(io.BytesIO(base64.b64decode(observation['image_png_base64']))))
        np.testing.assert_array_equal(decoded, pixels)

    def check_minigrid(self, observation, native):
        self.assertEqual(set(observation), set(native))
        self.assertEqual(observation['mission'], native['mission'])
        self.assertEqual(observation['direction'], native['direction'])
        np.testing.assert_array_equal(observation['image'], native['image'])


if __name__ == '__main__':
    unittest.main()
