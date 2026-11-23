"""2048 adapter/service regressions with a deterministic native-shaped double."""
import base64
import copy
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'game_first_exam/runtime')]
from config_schema import register_instance_schema, validate_instance
from grade import grade
from server import Game


def load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / 'game_first_exam/benchmarks/game2048' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


backend = load('game2048_adapter_test', 'adapter.py')
schema = register_instance_schema(load('game2048_schema_test', 'instance_schema.py'))
rules = load('game2048_rules_test', 'metric_rules.py')


class Space:
    n = 4
    shape = (4, 4, 16)


class Engine:
    """Small native-shaped engine: target on step two, game over on step three."""
    def __init__(self):
        self.unwrapped = self
        self.action_space = Space()
        self.observation_space = Space()
        self.np_random = np.random.default_rng(1)
        self.board = np.zeros((4, 4), dtype=np.uint8)
        self.step_score = 0
        self.total_score = 0
        self.is_legal = True
        self.illegal_count = 0
        self.actions = []
        self.reset_count = 0
        self.closed = False
        self.image = np.zeros((460, 400, 3), dtype=np.uint8)

    def _observation(self):
        out = np.zeros((4, 4, 16), dtype=np.uint8)
        rows, cols = np.indices(self.board.shape)
        out[rows, cols, self.board] = 1
        return out

    def _info(self):
        return {'board': self.board, 'step_score': self.step_score,
                'total_score': self.total_score, 'max': int(self.board.max()),
                'is_legal': self.is_legal, 'illegal_count': self.illegal_count}

    def reset(self, seed=None):
        self.reset_count += 1
        self.np_random = np.random.default_rng(seed)
        self.board.fill(0)
        self.board[0, 0], self.board[1, 1] = 1, 2
        self.step_score = self.total_score = self.illegal_count = 0
        self.is_legal = True
        self.image.fill(seed % 255)
        return self._observation(), self._info()

    def step(self, action):
        self.actions.append(action)
        self.step_score = 0
        if len(self.actions) == 1:
            self.board[0, 0] = 2
            self.step_score = 4
        elif len(self.actions) == 2:
            self.board[0, 1] = 11
            self.step_score = 2048
        elif action == 3:
            self.is_legal = False
            self.illegal_count += 1
        self.total_score += self.step_score
        terminated = len(self.actions) == 3
        self.image.fill(100 + len(self.actions))
        return self._observation(), self.step_score, terminated, False, self._info()

    def render(self):
        return self.image.copy()

    def close(self):
        self.closed = True


def instance():
    return {
        'schema_version': 'game-instance/2.2', 'protocol': 'game-standard/2.2',
        'adapter_version': '1.0.0', 'benchmark': 'game2048',
        'env_id': 'gymnasium_2048/TwentyFortyEight-v0', 'family': '2048-classic',
        'seed': 42, 'max_steps': 1000, 'initial_state_sha256': '0' * 64,
        'observation_profile': 'native-rgb-board-score-v1',
        'capabilities': {'images': True, 'action_mode': 'enum',
                         'timing': 'action-stepped', 'native_truncation': False},
        'engine_versions': dict(schema.ENGINE_VERSIONS),
        'board_size': 4, 'native_max_power': 16,
        'native_render_shape': [460, 400, 3], 'target_power': 11,
        'metric_spec': {'primary': 'native_score', 'reducer': 'family_macro',
                        'reducer_version': '1.0.0',
                        'success_label': '2048_tile_reached'},
    }


class Game2048ContractTests(unittest.TestCase):
    def setUp(self):
        self.factory = patch.object(backend, 'make_native_env', side_effect=lambda _: Engine())
        self.factory.start()
        self.addCleanup(self.factory.stop)
        self.versions = patch.object(backend.importlib.metadata, 'version',
                                     side_effect=schema.ENGINE_VERSIONS.__getitem__)
        self.versions.start()
        self.addCleanup(self.versions.stop)

    def adapter(self):
        adapter = backend.Adapter(instance())
        self.addCleanup(adapter.close)
        return adapter

    def test_runtime_and_test_dependency_locks_match(self):
        runtime = ROOT / 'game_first_exam/benchmarks/game2048/requirements.txt'
        lock = ROOT / 'game_first_exam/tests/envs/locks/game2048.txt'
        self.assertEqual(runtime.read_text(), lock.read_text())

    def test_native_profile_and_all_four_actions(self):
        adapter = self.adapter()
        self.assertEqual(adapter.env.reset_count, 1)
        self.assertEqual(adapter.frame().shape, (460, 400, 3))
        for name, index in backend.ACTIONS.items():
            with self.subTest(action=name):
                other = self.adapter()
                other.step(name)
                self.assertEqual(other.env.actions, [index])

    def test_public_observation_is_only_cached_rgb(self):
        adapter = self.adapter()
        before = adapter.fingerprint()
        for _ in range(3):
            observation = adapter.observe()
            self.assertEqual(set(observation), {'image_png_base64'})
            decoded = np.asarray(Image.open(io.BytesIO(
                base64.b64decode(observation['image_png_base64']))))
            np.testing.assert_array_equal(decoded, adapter.frame())
            adapter.spec(); adapter.metrics()
        self.assertEqual(adapter.fingerprint(), before)
        changed = adapter.frame(); changed.fill(255)
        self.assertEqual(adapter.fingerprint(), before)

    def test_public_service_excludes_privileged_native_state(self):
        adapter = self.adapter()
        config = instance(); config['initial_state_sha256'] = adapter.fingerprint()
        with tempfile.TemporaryDirectory() as directory:
            game = Game(adapter, config, directory)
            try:
                public = [game.spec(), game.observe(), game.submit({
                    'action': 'UP', 'expected_step': 0, 'request_id': 'isolation-audit'})]
                forbidden = {'seed', 'target_power', 'engine_versions', 'board', 'rng',
                             'fingerprint', 'metrics', 'native_score', 'native_return',
                             'max_tile', 'initial_state_sha256', 'is_legal'}

                def keys(value):
                    if isinstance(value, dict):
                        return set(value) | set().union(*(keys(v) for v in value.values()), set())
                    if isinstance(value, list):
                        return set().union(*(keys(v) for v in value), set())
                    return set()

                self.assertFalse(forbidden & set().union(*(keys(item) for item in public)))
                self.assertEqual(set(public[1]['observation']), {'image_png_base64'})
                self.assertEqual(set(public[2]['observation']), {'image_png_base64'})
            finally:
                game.close()

    def test_native_score_target_and_game_over(self):
        adapter = self.adapter()
        self.assertEqual(adapter.step('UP').reward, 4)
        self.assertEqual(adapter.step('RIGHT').reward, 2048)
        self.assertTrue(adapter.success())
        transition = adapter.step('DOWN')
        self.assertTrue(transition.terminated)
        self.assertFalse(transition.truncated)
        self.assertEqual(adapter.metrics(), {
            'target_reached': 1, 'native_score': 2052, 'max_tile': 2048,
            'valid_moves': 3, 'invalid_moves': 0, 'native_return': 2052.0,
        })
        with self.assertRaisesRegex(ValueError, 'episode closed'):
            adapter.step('UP')

    def test_invalid_action_does_not_advance(self):
        adapter = self.adapter()
        with self.assertRaisesRegex(ValueError, 'unknown 2048 action'):
            adapter.step('RESET')
        self.assertEqual(adapter.env.actions, [])

    def test_shared_service_deduplicates_seals_and_grades(self):
        adapter = self.adapter()
        config = instance(); config['initial_state_sha256'] = adapter.fingerprint()
        with tempfile.TemporaryDirectory() as directory:
            game = Game(adapter, config, directory)
            try:
                first = {'action': 'UP', 'expected_step': 0, 'request_id': 'one'}
                response = game.submit(first)
                self.assertEqual(game.submit(first), response)
                game.submit({'action': 'RIGHT', 'expected_step': 1, 'request_id': 'two'})
                game.submit({'action': 'DOWN', 'expected_step': 2, 'request_id': 'three'})
                self.assertEqual(len(adapter.env.actions), 3)
                result = grade(game.final, config, rules.validate_metrics)
                self.assertEqual((result['primary_score'], result['success']), (2052, 1))
                corrupted = copy.deepcopy(game.final)
                corrupted['metrics']['native_score'] = 0
                with self.assertRaises(ValueError):
                    grade(corrupted, config, rules.validate_metrics)
            finally:
                game.close()

    def test_schema_rejects_profile_drift(self):
        validate_instance(instance())
        for key, value in [('board_size', 5), ('native_max_power', 17),
                           ('native_render_shape', [400, 400, 3]), ('target_power', 10),
                           ('max_steps', None), ('unknown', True)]:
            config = instance(); config[key] = value
            with self.subTest(key=key), self.assertRaises((ValueError, TypeError)):
                validate_instance(config)

    def test_zero_action_finish_is_valid_failure(self):
        adapter = self.adapter()
        config = instance(); config['initial_state_sha256'] = adapter.fingerprint()
        with tempfile.TemporaryDirectory() as directory:
            game = Game(adapter, config, directory)
            try:
                game.finalize('agent_finished')
                result = grade(game.final, config, rules.validate_metrics)
                self.assertEqual((result['primary_score'], result['success']), (0, 0))
            finally:
                game.close()


if __name__ == '__main__':
    unittest.main()
