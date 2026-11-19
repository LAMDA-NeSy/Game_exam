"""Adapter/service regression tests with an explicit deterministic engine double."""
import copy
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'game_first_exam/runtime')]
from config_schema import register_instance_schema, validate_instance
from grade import grade
from server import Game


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'game_first_exam/benchmarks/coinrun' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


with patch.dict(sys.modules, {'procgen': types.SimpleNamespace(ProcgenGym3Env=None)}):
    backend = load('coinrun_adapter_test', 'adapter.py')
schema = register_instance_schema(load('coinrun_schema_test', 'instance_schema.py'))
rules = load('coinrun_rules_test', 'metric_rules.py')


class Engine:
    """Simulate gym3's automatic reset and reused image buffer."""
    complete = True

    def __init__(self, **options):
        self.options = options
        self.actions = []
        self.image = np.zeros((1, 64, 64, 3), dtype=np.uint8)
        self.closed = False

    def observe(self):
        ended = len(self.actions) == 2
        self.image.fill(200 if ended else len(self.actions))
        return np.array([10.0 if ended and self.complete else 0.0]), {'rgb': self.image}, np.array([not self.actions or ended])

    def act(self, action):
        self.actions.append(int(action[0]))

    def get_info(self):
        return [{'prev_level_complete': self.complete, 'prev_level_seed': 42}]

    def get_state(self):
        return [bytes(self.actions)]

    def close(self):
        self.closed = True


def instance():
    return {'schema_version': 'game-instance/2.2', 'protocol': 'game-standard/2.2',
            'adapter_version': '1.0.0', 'benchmark': 'coinrun', 'env_id': 'procgen-coinrun-v0',
            'family': 'coinrun-hard', 'seed': 42, 'max_steps': None, 'native_max_steps': 1000,
            'initial_state_sha256': '0' * 64, 'observation_profile': 'native-rgb-64-v1',
            'capabilities': {'images': True, 'action_mode': 'enum', 'timing': 'action-stepped',
                             'native_truncation': False},
            'engine_versions': dict(schema.ENGINE_VERSIONS), 'distribution_mode': 'hard',
            'metric_spec': {'primary': 'completion_score', 'reducer': 'family_macro',
                            'reducer_version': '1.0.0', 'success_label': 'native_level_complete'}}


class CoinRunContractTests(unittest.TestCase):
    def setUp(self):
        self.engine_patch = patch.object(backend, 'ProcgenGym3Env', Engine)
        self.engine_patch.start()
        self.addCleanup(self.engine_patch.stop)
        self.version_patch = patch.object(backend.importlib.metadata, 'version',
                                          side_effect=schema.ENGINE_VERSIONS.__getitem__)
        self.version_patch.start()
        self.addCleanup(self.version_patch.stop)

    def adapter(self):
        adapter = backend.Adapter(instance())
        self.addCleanup(adapter.close)
        return adapter

    def test_native_options_and_all_fifteen_actions(self):
        adapter = self.adapter()
        self.assertEqual(adapter.env.options, dict(num=1, env_name='coinrun', num_levels=1,
            start_level=42, rand_seed=42, num_threads=1, distribution_mode='hard',
            use_sequential_levels=False, paint_vel_info=False))
        for index, action in enumerate(backend.ACTIONS):
            with self.subTest(action=action):
                other = self.adapter()
                other.step(action)
                self.assertEqual(other.env.actions, [index])

    def test_read_methods_preserve_state_and_expose_only_image(self):
        adapter = self.adapter()
        before = adapter.fingerprint()
        for _ in range(3):
            self.assertEqual(set(adapter.observe()), {'image_png_base64'})
            adapter.spec()
            adapter.metrics()
            adapter.frame().fill(255)
        self.assertEqual(adapter.fingerprint(), before)
        self.assertEqual(adapter.env.actions, [])

    def test_first_terminal_reward_and_auto_reset_frame(self):
        adapter = self.adapter()
        self.assertFalse(adapter.step('RIGHT').terminated)
        frame = adapter.frame()
        transition = adapter.step('RIGHT_UP')
        self.assertEqual(transition.reward, 10)
        self.assertTrue(transition.terminated)
        np.testing.assert_array_equal(adapter.frame(), frame)
        self.assertTrue(adapter.success())
        with self.assertRaisesRegex(ValueError, 'episode closed'):
            adapter.step('NOOP')
        self.assertEqual(len(adapter.env.actions), 2)

    def test_failure_is_zero_and_has_native_boundary(self):
        with patch.object(Engine, 'complete', False):
            adapter = self.adapter()
            adapter.step('RIGHT')
            self.assertTrue(adapter.step('RIGHT').terminated)
            self.assertFalse(adapter.success())
            self.assertEqual(adapter.metrics()['native_return'], 0)

    def test_invalid_action_does_not_advance(self):
        adapter = self.adapter()
        with self.assertRaises(ValueError):
            adapter.step('RESET')
        self.assertEqual(adapter.steps, 0)
        self.assertEqual(adapter.env.actions, [])

    def test_shared_service_deduplicates_seals_and_grades(self):
        adapter = self.adapter()
        config = instance()
        config['initial_state_sha256'] = adapter.fingerprint()
        with tempfile.TemporaryDirectory() as directory:
            game = Game(adapter, config, directory)
            try:
                request = {'action': 'RIGHT', 'expected_step': 0, 'request_id': 'one'}
                response = game.submit(request)
                self.assertEqual(game.submit(request), response)
                game.submit({'action': 'RIGHT_UP', 'expected_step': 1, 'request_id': 'two'})
                self.assertEqual(len(adapter.env.actions), 2)
                self.assertTrue(game.observe()['done'])
                result = grade(game.final, config, rules.validate_metrics)
                self.assertEqual(result['primary_score'], 100)
                with self.assertRaisesRegex(ValueError, 'episode closed'):
                    game.submit({'action': 'RIGHT', 'expected_step': 2, 'request_id': 'three'})
                corrupted = copy.deepcopy(game.final)
                corrupted['metrics']['completion_score'] = 0
                with self.assertRaises(ValueError):
                    grade(corrupted, config, rules.validate_metrics)
            finally:
                game.close()

    def test_proposed_schema_rejects_configuration_drift(self):
        validate_instance(instance())
        for key, value in [('distribution_mode', 'extreme'), ('family', 'other'),
                           ('max_steps', 10), ('unknown', True)]:
            config = instance()
            config[key] = value
            with self.subTest(key=key), self.assertRaises((ValueError, TypeError)):
                validate_instance(config)

    def test_zero_action_and_public_time_limit_are_valid_failures(self):
        for reason in ('agent_finished', 'time_limit'):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as directory:
                adapter = self.adapter()
                config = instance()
                config['initial_state_sha256'] = adapter.fingerprint()
                game = Game(adapter, config, directory)
                try:
                    game.finalize(reason)
                    result = grade(game.final, config, rules.validate_metrics)
                    self.assertTrue(result['result_valid'])
                    self.assertEqual(result['primary_score'], 0)
                    self.assertEqual(adapter.env.actions, [])
                finally:
                    game.close()

    def test_frozen_versions_and_limit_reject_drift(self):
        for key, value in [('engine_versions', {**schema.ENGINE_VERSIONS, 'procgen': '0.10.6'}),
                           ('native_max_steps', 500), ('native_max_steps', True)]:
            config = instance()
            config[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_instance(config)


if __name__ == '__main__':
    unittest.main()
