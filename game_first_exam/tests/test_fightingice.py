"""Configuration checks by default; --native requires the installed real Java engine."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import shutil
import subprocess
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'game_first_exam/runtime')]
from game_schemas import register_schemas
from config_schema import validate_instance

register_schemas()
TASKS = sorted((ROOT / 'game_first_exam/tasks/fightingice').glob('*-standard'))
BENCH = ROOT / 'game_first_exam/benchmarks/fightingice'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RULES = load('fightingice_metrics', BENCH / 'metric_rules.py')


class Configuration(unittest.TestCase):
    def test_frozen_match_parameters_fail_closed(self):
        self.assertEqual(len(TASKS), 2)
        for task in TASKS:
            instance = json.loads((task / 'tests/instance.json').read_text())
            validate_instance(instance)
            for change in ({'player': True}, {'player': 2}, {'rounds': 1}, {'initial_hp': 401},
                           {'round_frames': 3601}, {'seed': 1}, {'opponent': 'arbitrary'},
                           {'max_steps': 100}, {'observation_profile': 'non-delay'},
                           {'characters': ['GARNET', 'ZEN']}, {'unexpected': True}):
                with self.subTest(change=change), self.assertRaises((ValueError, TypeError)):
                    validate_instance({**instance, **change})

    def test_round_scores_and_partial_matches(self):
        instance = json.loads((TASKS[0] / 'tests/instance.json').read_text())
        rounds = [{'current_round': i, 'remaining_hps': [400, 364], 'elapsed_frame': 3600}
                  for i in range(1, 4)]
        metrics = {'rounds': rounds, 'wins': 3, 'losses': 0, 'draws': 0, 'completed_rounds': 3,
                   'round_win_score': 100.0, 'native_steps': 10800}
        final = {'metrics': metrics, 'steps': 10800, 'terminated': True, 'truncated': False,
                 'return': 0.0, 'success': True}
        RULES.validate_metrics(final, instance)
        for change in ({'round_win_score': 99}, {'wins': True}, {'native_steps': 10801},
                       {'draws': 1}, {'completed_rounds': 2}, {'round_win_score': float('nan')}):
            altered = copy.deepcopy(final)
            altered['metrics'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                RULES.validate_metrics(altered, instance)
        partial = copy.deepcopy(final)
        partial.update(steps=3600, terminated=False, success=False)
        partial['metrics'].update(rounds=rounds[:1], completed_rounds=1, wins=1,
                                  round_win_score=100/3, native_steps=3600)
        RULES.validate_metrics(partial, instance)
        partial['metrics']['round_win_score'] = 100
        with self.assertRaises(ValueError):
            RULES.validate_metrics(partial, instance)
        impossible = copy.deepcopy(final)
        impossible['metrics']['rounds'][0]['elapsed_frame'] = 10
        with self.assertRaises(ValueError):
            RULES.validate_metrics(impossible, instance)

    def test_public_images_do_not_contain_the_engine_or_solution(self):
        for task in TASKS:
            dockerfile = (task / 'environment/Dockerfile').read_text()
            for forbidden in ('FightingICE.jar', 'bridge.py', 'instance.json', 'control.py', '/solution', '/tests'):
                self.assertNotIn(forbidden, dockerfile)
            self.assertNotIn('ports:', (task / 'environment/docker-compose.yaml').read_text())
            self.assertIn('SERVER_HOST=127.0.0.1', (task / 'environment/sim/Dockerfile').read_text())


class Native(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(BENCH))
        cls.adapter = load('fightingice_adapter', BENCH / 'adapter.py')

    def test_native_delay_pause_key_mapping_and_cleanup(self):
        instance = json.loads((TASKS[0] / 'tests/instance.json').read_text())
        adapter = self.adapter.Adapter(instance)
        process = adapter.process
        try:
            self.assertEqual(adapter.fingerprint(), instance['initial_state_sha256'])
            self.assertTrue(adapter.observe()['frame_data']['empty_flag'])
            initial = adapter.fingerprint()
            for _ in range(3):
                adapter.spec(); adapter.observe(); adapter.frame()
            time.sleep(.2)
            self.assertEqual(adapter.fingerprint(), initial)
            port = int(process.args[-1])
            listeners = [line.split()[1].split(':')[0]
                         for path in ('/proc/net/tcp', '/proc/net/tcp6')
                         for line in Path(path).read_text().splitlines()[1:]
                         if line.split()[3] == '0A' and int(line.split()[1].split(':')[1], 16) == port]
            self.assertEqual(len(listeners), 1)
            self.assertIn(listeners[0], ('0100007F', '0000000000000000FFFF00000100007F'))
            for _ in range(20):
                adapter.step('R')
            observation = adapter.observe()
            self.assertEqual(set(observation), {'player', 'frame_data', 'is_control'})
            self.assertNotIn('non_delay_frame_data', observation)
            self.assertEqual(observation['frame_data']['current_frame_number'], 6)
            self.assertGreater(adapter.audit['current_frame_number'], observation['frame_data']['current_frame_number'])
            with self.assertRaises(ValueError):
                adapter.step('reset')
            with self.assertRaises(ValueError):
                adapter.step('RB')  # non-canonical key order
        finally:
            adapter.close()
        self.assertIsNotNone(process.poll())
        self.assertFalse(adapter.session.thread.is_alive())

    def test_reference_matches_live_grading_and_evidence(self):
        from grade import grade
        from server import Game, InvalidAction
        for task in TASKS:
            instance = json.loads((task / 'tests/instance.json').read_text())
            reference = load('fightingice_reference', task / 'solution/control.py')
            with self.subTest(player=instance['player']), tempfile.TemporaryDirectory() as output:
                game = Game(self.adapter.Adapter(instance), instance, output)
                try:
                    self.assertIsNone(game.final)
                    with self.assertRaises(InvalidAction):
                        game.submit({'action': 'reset', 'expected_step': 0, 'request_id': 'bad'})
                    while game.final is None:
                        body = {'action': reference.choose(game.observe()['observation']),
                                'expected_step': game.steps, 'request_id': str(game.steps)}
                        reply = game.submit(body)
                        if game.steps == 1:
                            self.assertEqual(game.submit(body), reply)
                            self.assertEqual(game.steps, 1)
                    verdict = grade(game.final, instance, RULES.validate_metrics)
                    self.assertEqual((verdict['success'], verdict['primary_score'], verdict['infra_error']), (1, 100, 0))
                    self.assertEqual(verdict['steps'], 10800)
                    recording = json.loads((Path(output) / 'recording.json').read_text())
                    self.assertIsNone(recording['render_error'])
                    self.assertGreater((Path(output) / 'replay.mp4').stat().st_size, 1000)
                    with self.assertRaises(ValueError):
                        game.submit({'action': 'noop', 'expected_step': game.steps, 'request_id': 'after'})
                finally:
                    game.close()

    def test_no_keys_draw_and_early_exit_failures(self):
        from grade import grade
        from server import Game
        instance = json.loads((TASKS[0] / 'tests/instance.json').read_text())
        adapter = self.adapter.Adapter(instance)
        try:
            while not adapter.done:
                adapter.step('noop')
            self.assertEqual((adapter.metrics()['draws'], adapter.metrics()['round_win_score']), (3, 0))
            self.assertFalse(adapter.success())
        finally:
            adapter.close()
        with tempfile.TemporaryDirectory() as output:
            game = Game(self.adapter.Adapter(instance), instance, output)
            try:
                game.finalize('agent_finished')
                result = grade(game.final, instance, RULES.validate_metrics)
                self.assertEqual((result['success'], result['primary_score'], result['infra_error']), (0, 0, 0))
                self.assertFalse(game.final['terminated'])
            finally:
                game.close()

    def test_repeated_native_inputs_preserve_gameplay_and_engine_fault_is_invalid(self):
        from grade import grade
        from server import EnvironmentFault, Game
        instance = json.loads((TASKS[0] / 'tests/instance.json').read_text())
        traces = []
        for _ in range(2):
            adapter = self.adapter.Adapter(instance)
            try:
                trace = [adapter.fingerprint()]
                for index in range(200):
                    adapter.step('R' if index < 60 else 'BDR')
                    trace.append(adapter.fingerprint())
                traces.append(trace)
            finally:
                adapter.close()
        self.assertEqual(traces[0], traces[1])
        with tempfile.TemporaryDirectory() as output:
            game = Game(self.adapter.Adapter(instance), instance, output)
            try:
                game.adapter.process.kill()
                game.adapter.process.wait(timeout=5)
                with self.assertRaises(EnvironmentFault):
                    game.submit({'action': 'noop', 'expected_step': 0, 'request_id': 'engine-fault'})
                verdict = grade(game.final, instance, RULES.validate_metrics)
                self.assertEqual(verdict['environment_error'], 1)
                self.assertIsNone(verdict['primary_score'])
            finally:
                game.close()

    def test_native_http_client_and_separate_stdlib_verifier(self):
        from http.server import HTTPServer
        sys.path.insert(0, str(ROOT / 'shared/connection'))
        from game_client import GameClient
        from server import Game, Handler
        instance = json.loads((TASKS[0] / 'tests/instance.json').read_text())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            game = Game(self.adapter.Adapter(instance), instance, output)
            server = HTTPServer(('127.0.0.1', 0), Handler)
            server.game = game
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                client = GameClient(f'http://127.0.0.1:{server.server_port}')
                self.assertEqual(client.spec()['game_data']['character_names'], ['ZEN', 'ZEN'])
                reply = client.observe()
                for _ in range(20):
                    reply = client.step('R', reply['step'])
                self.assertEqual(reply['step'], 20)
                self.assertEqual(set(reply['observation']), {'player', 'frame_data', 'is_control'})
                game.finalize('agent_finished')
                verifier = output / 'verifier'
                verifier.mkdir()
                for name in ('grade', 'config_schema', 'reducers'):
                    shutil.copyfile(ROOT / f'game_first_exam/runtime/{name}.py', verifier / f'{name}.py')
                for name in ('instance_schema', 'metric_rules'):
                    shutil.copyfile(BENCH / f'{name}.py', verifier / f'{name}.py')
                subprocess.run([sys.executable, '-S', str(verifier / 'grade.py'),
                                '--evidence', str(output / 'final.json'),
                                '--instance', str(TASKS[0] / 'tests/instance.json'),
                                '--output', str(verifier)], check=True, capture_output=True)
                metrics = json.loads((verifier / 'metrics.json').read_text())
                self.assertEqual((metrics['primary_score'], metrics['infra_error']), (0, 0))
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()
                game.close()


if __name__ == '__main__':
    native = '--native' in sys.argv
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Configuration)
    if native:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Native))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
