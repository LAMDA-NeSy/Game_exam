"""Run against each game's own pinned dependency environment, never a mock simulator."""
import copy
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'game_first_exam/runtime'))
sys.path.insert(0, str(ROOT / 'scripts'))
from game_schemas import register_schemas

register_schemas()
from grade import grade
from server import Game

BENCHMARK = os.environ.get('GAME_TEST_BENCHMARK', 'minigrid')


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, filename)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


class NativeAdapters(unittest.TestCase):
    def construct(self, module, instance, assets):
        # Observe the native reset, rather than trusting a self-reported initialization counter.
        owner, name = {"minihack": (getattr(module, "gym", None), "make"),
                       "minigrid": (getattr(module, "gym", None), "make"),
                       "babaisai": (getattr(module, "baba", None), "make"),
                       "crafter": (getattr(module, "crafter", None), "Env"),
                       "textworld": (getattr(module, "textworld", None), "start")}[BENCHMARK]
        original = getattr(owner, name)
        created = []
        def factory(*args, **kwargs):
            env = original(*args, **kwargs)
            reset = env.reset
            count = [0]
            def counted(*a, **kw):
                count[0] += 1
                if count[0] > 1:
                    raise AssertionError("environment was reset more than once")
                return reset(*a, **kw)
            env.reset = counted
            created.append((env, count))
            return env
        with patch.object(owner, name, factory):
            adapter = module.Adapter(instance, assets)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0][1][0], 1)
        return adapter

    def assert_read_only(self, adapter):
        before = adapter.fingerprint()
        for _ in range(2):
            adapter.spec(); adapter.observe(); adapter.frame()
        self.assertEqual(adapter.fingerprint(), before)

    def test_frozen_references_live_evidence_and_failed_submissions(self):
        adapter_module = module('native_adapter', ROOT / f'game_first_exam/benchmarks/{BENCHMARK}/adapter.py')
        rules = module('native_rules', ROOT / f'game_first_exam/benchmarks/{BENCHMARK}/metric_rules.py')
        tasks = sorted((ROOT / 'game_first_exam/tasks' / BENCHMARK).glob('*-standard'))
        tasks = [task for task in tasks if '-i00-' not in task.name]
        self.assertTrue(tasks)
        for task in tasks:
            instance = json.loads((task / 'tests/instance.json').read_text())
            with self.subTest(task=task.name), tempfile.TemporaryDirectory() as out:
                adapter = self.construct(adapter_module, instance, task / 'environment/sim')
                game = Game(adapter, instance, out)
                self.assertIsNone(game.final)
                native_env = adapter.env
                self.assert_read_only(adapter)
                initial = adapter.fingerprint()
                for _ in range(4):
                    game.observe(); adapter.frame()
                self.assertEqual(adapter.fingerprint(), initial, 'reading/rendering must not consume native RNG')
                if BENCHMARK == 'textworld':
                    self.assertEqual(set(adapter.observe()), {'feedback', 'inventory', 'description', 'objective'})
                for forbidden in ['restart', 'undo', 'restore', 'tw-print-state', 'reset', 'look\nrestart', 'look then restart', 'go north and then undo', 'print_state', 'enable print state option', 'q']:
                    with self.assertRaises(ValueError):
                        game.submit({'action': forbidden, 'expected_step': 0, 'request_id': forbidden})
                self.assertEqual(game.steps, 0)
                for action in json.loads((task / 'solution/actions.json').read_text()):
                    if game.final is not None: break
                    game.submit({'action': action, 'expected_step': game.steps, 'request_id': str(game.steps)})
                    self.assertIs(adapter.env, native_env)
                    self.assert_read_only(adapter)
                    if BENCHMARK == 'textworld':
                        self.assertEqual(game.reward, adapter.score)
                if BENCHMARK == 'crafter' and game.final is None:
                    game.finalize('agent_finished')
                self.assertIsNotNone(game.final)
                before = adapter.fingerprint()
                with self.assertRaises(ValueError):
                    game.submit({'action': action, 'expected_step': game.steps, 'request_id': 'after-final'})
                self.assertEqual(adapter.fingerprint(), before)
                result = grade(game.final, instance, rules.validate_metrics)
                self.assertEqual(result['success'], 1)
                self.assertEqual(result['infra_error'], 0)
                recording = json.loads((Path(out) / 'recording.json').read_text())
                self.assertIsNone(recording['render_error'])
                self.assertGreater((Path(out) / 'replay.mp4').stat().st_size, 1000)
                altered = copy.deepcopy(game.final)
                altered['metrics'][instance['metric_spec']['primary']] = 99
                with self.assertRaises(ValueError):
                    grade(altered, instance, rules.validate_metrics)
                game.close()
            with tempfile.TemporaryDirectory() as out:
                game = Game(self.construct(adapter_module, instance, task / 'environment/sim'), instance, out)
                game.finalize('agent_finished')
                result = grade(game.final, instance, rules.validate_metrics)
                self.assertEqual((result['success'], result['steps'], result['primary_score']), (0, 0, 0))
                game.close()


if __name__ == '__main__':
    unittest.main()
