"""Tetris adapter/service regressions with a deterministic engine double."""
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
        name, ROOT / 'game_first_exam/benchmarks/tetris' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


backend = load('tetris_adapter_test', 'adapter.py')
schema = register_instance_schema(load('tetris_schema_test', 'instance_schema.py'))
rules = load('tetris_rules_test', 'metric_rules.py')


class Piece:
    def __init__(self, piece_id):
        self.id = piece_id
        self.matrix = np.full((2, 2), piece_id, dtype=np.uint8)


class Queue:
    size = 4

    def __init__(self):
        self.queue = [1, 2, 3, 4]


class Holder:
    size = 1

    def __init__(self):
        self.queue = []


class Randomizer:
    def __init__(self):
        self.bag = np.arange(7, dtype=np.int8)
        self.index = 4
        self.rng = np.random.default_rng(1)


class Engine:
    """Small native-shaped engine: line clear on step two, game over on step three."""
    width = 10
    height = 20
    gravity_enabled = True
    padding = 4
    width_padded = 18
    height_padded = 24

    def __init__(self):
        self.unwrapped = self
        self.queue = Queue()
        self.holder = Holder()
        self.randomizer = Randomizer()
        self.active_tetromino = Piece(2)
        self.board = np.zeros((24, 18), dtype=np.uint8)
        self.x, self.y = 8, 0
        self.has_swapped = False
        self.game_over = False
        self.actions = []
        self.reset_count = 0
        self.closed = False
        self.image = np.zeros((24, 34, 3), dtype=np.uint8)

    def reset(self, seed=None):
        self.reset_count += 1
        self.randomizer.rng = np.random.default_rng(seed)
        self.image.fill(seed % 255)
        return self.image.copy(), {'lines_cleared': 0}

    def step(self, action):
        self.actions.append(action)
        self.x += 1
        self.board[0, len(self.actions)] = action + 2
        lines = 1 if len(self.actions) == 2 else 0
        terminated = len(self.actions) == 3
        reward = 0 if terminated else (11 if lines else 0)
        self.game_over = terminated
        self.image.fill(200 if terminated else len(self.actions))
        return self.image.copy(), reward, terminated, False, {'lines_cleared': lines}

    def close(self):
        self.closed = True


def instance():
    return {
        'schema_version': 'game-instance/2.2', 'protocol': 'game-standard/2.2',
        'adapter_version': '1.0.0', 'benchmark': 'tetris',
        'env_id': 'tetris_gymnasium/Tetris', 'family': 'tetris-classic',
        'seed': 42, 'max_steps': 1000, 'initial_state_sha256': '0' * 64,
        'observation_profile': 'native-rgb-board-queue-holder-v1',
        'capabilities': {'images': True, 'action_mode': 'enum',
                         'timing': 'action-stepped', 'native_truncation': False},
        'engine_versions': dict(schema.ENGINE_VERSIONS),
        'board_width': 10, 'board_height': 20, 'gravity': True,
        'native_queue_size': 4, 'native_holder_size': 1, 'target_lines': 1,
        'metric_spec': {'primary': 'lines_cleared', 'reducer': 'family_macro',
                        'reducer_version': '1.0.0',
                        'success_label': 'target_lines_reached'},
    }


class TetrisContractTests(unittest.TestCase):
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
        runtime = ROOT / 'game_first_exam/benchmarks/tetris/requirements.txt'
        lock = ROOT / 'game_first_exam/tests/envs/locks/tetris.txt'
        self.assertEqual(runtime.read_text(), lock.read_text())

    def test_native_profile_and_all_eight_actions(self):
        adapter = self.adapter()
        self.assertEqual(adapter.env.reset_count, 1)
        self.assertEqual(adapter.frame().shape, (24, 34, 3))
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
            adapter.spec()
            adapter.metrics()
        self.assertEqual(adapter.fingerprint(), before)
        changed = adapter.frame()
        changed.fill(255)
        self.assertEqual(adapter.fingerprint(), before)

    def test_public_service_excludes_privileged_native_state(self):
        adapter = self.adapter()
        config = instance()
        config['initial_state_sha256'] = adapter.fingerprint()
        with tempfile.TemporaryDirectory() as directory:
            game = Game(adapter, config, directory)
            try:
                public = [game.spec(), game.observe(), game.submit({
                    'action': 'NO_OP', 'expected_step': 0, 'request_id': 'isolation-audit'})]
                forbidden = {'seed', 'target_lines', 'engine_versions', 'board', 'rng', 'bag',
                             'fingerprint', 'metrics', 'native_return', 'lines_cleared',
                             'initial_state_sha256'}

                def keys(value):
                    if isinstance(value, dict):
                        nested = set().union(*(keys(item) for item in value.values()), set())
                        return set(value) | nested
                    if isinstance(value, list):
                        return set().union(*(keys(item) for item in value), set())
                    return set()

                self.assertFalse(forbidden & set().union(*(keys(item) for item in public)))
                self.assertEqual(set(public[1]['observation']), {'image_png_base64'})
                self.assertEqual(set(public[2]['observation']), {'image_png_base64'})
            finally:
                game.close()

    def test_line_reward_target_and_native_game_over(self):
        adapter = self.adapter()
        self.assertEqual(adapter.step('MOVE_LEFT').reward, 0)
        transition = adapter.step('HARD_DROP')
        self.assertEqual(transition.reward, 11)
        self.assertTrue(adapter.success())
        self.assertEqual(adapter.metrics(), {
            'success': 1, 'lines_cleared': 1, 'native_return': 11.0,
            'rewarded_placements': 1, 'line_clear_score': 10,
        })
        transition = adapter.step('NO_OP')
        self.assertTrue(transition.terminated)
        self.assertFalse(transition.truncated)
        with self.assertRaisesRegex(ValueError, 'episode closed'):
            adapter.step('NO_OP')

    def test_invalid_action_does_not_advance(self):
        adapter = self.adapter()
        with self.assertRaisesRegex(ValueError, 'unknown Tetris action'):
            adapter.step('RESET')
        self.assertEqual(adapter.env.actions, [])

    def test_shared_service_deduplicates_seals_and_grades(self):
        adapter = self.adapter()
        config = instance()
        config['initial_state_sha256'] = adapter.fingerprint()
        with tempfile.TemporaryDirectory() as directory:
            game = Game(adapter, config, directory)
            try:
                first = {'action': 'MOVE_LEFT', 'expected_step': 0, 'request_id': 'one'}
                response = game.submit(first)
                self.assertEqual(game.submit(first), response)
                game.submit({'action': 'HARD_DROP', 'expected_step': 1, 'request_id': 'two'})
                game.submit({'action': 'NO_OP', 'expected_step': 2, 'request_id': 'three'})
                self.assertTrue(game.observe()['done'])
                self.assertEqual(len(adapter.env.actions), 3)
                result = grade(game.final, config, rules.validate_metrics)
                self.assertEqual((result['primary_score'], result['success']), (1, 1))
                corrupted = copy.deepcopy(game.final)
                corrupted['metrics']['lines_cleared'] = 0
                with self.assertRaises(ValueError):
                    grade(corrupted, config, rules.validate_metrics)
            finally:
                game.close()

    def test_schema_rejects_profile_drift(self):
        validate_instance(instance())
        for key, value in [('seed', 0), ('board_width', 12), ('gravity', False),
                           ('native_queue_size', 5), ('max_steps', None),
                           ('target_lines', 0), ('unknown', True)]:
            config = instance()
            config[key] = value
            with self.subTest(key=key), self.assertRaises((ValueError, TypeError)):
                validate_instance(config)

    def test_zero_action_finish_is_valid_failure(self):
        adapter = self.adapter()
        config = instance()
        config['initial_state_sha256'] = adapter.fingerprint()
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
