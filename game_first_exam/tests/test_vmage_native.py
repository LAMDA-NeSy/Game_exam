"""V-MAGE native-run equivalence; each episode owns a fresh Python process.

The baseline executes upstream PygameBase.run unchanged. Only its input source
is replaced with frozen legal actions. Native step, render, init_run, screenshot
capture and ledger bookkeeping are exercised independently of the bridge.
"""
import base64
import copy
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'game_first_exam/runtime'
GAMES = ('race', 'flappybird', 'pong', 'supermario', 'tempestrun')
CLASSES = dict(zip(GAMES, ('RaceGame', 'FlappyBirdGame', 'PongGame', 'SuperMarioGame', 'TempestRunGame')))
REFERENCES = {
    'race': ['RIGHT'] * 3 + ['DOWN'],
    'flappybird': ['UP'] * 3 + ['KEEP'] * 37,
    'pong': ['RIGHTUP', 'NONE', 'NONE', 'RIGHTDOWN', 'NONE', 'NONE', 'RIGHTDOWN', 'NONE', 'RIGHTDOWN', 'NONE', 'NONE', 'RIGHTDOWN', 'NONE', 'RIGHTDOWN', 'NONE', 'NONE', 'RIGHTDOWN', 'NONE', 'RIGHTDOWN', 'NONE', 'NONE', 'RIGHTDOWN', 'NONE', 'RIGHTDOWN', 'NONE', 'NONE', 'RIGHTDOWN', 'NONE', 'RIGHTDOWN'],
    'supermario': ['UP+RIGHT'] * 11,
    'tempestrun': ['NONE'] * 2,
}
EXPECTED_SCORE = {'race': 100, 'flappybird': 1, 'pong': 1, 'supermario': 100, 'tempestrun': 10}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def register_schemas():
    from config_schema import register_instance_schema, _SCHEMAS
    for game in GAMES:
        name = 'vmage_' + game
        if name not in _SCHEMAS:
            register_instance_schema(module('_test_' + name + '_schema', ROOT / f'game_first_exam/benchmarks/vmage/{game}/instance_schema.py'))


def task_for(game):
    level = int(os.environ.get('VMAGE_TEST_LEVEL', '1'))
    tasks = list((ROOT / 'game_first_exam/tasks/vmage').glob(f'vmage-{game}-l{level:02}-i01-standard'))
    if len(tasks) != 1:
        raise AssertionError('expected one frozen task for ' + game)
    return tasks[0]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def native_state(g, game):
    """Explicit physical/RNG state, independent of bridge fingerprint code.

    Tempest's wall-clock explosion timestamps and render caches are deliberately
    excluded; its obstacle identities, flags and geometry are included. We do
    not claim deterministic explosion pixels across different real-time runs.
    """
    import numpy as np
    import pygame
    state = {'score': g.score, 'over': bool(g.over), 'ledger': len(g.game_frames),
             'python_rng': digest(random.getstate()),
             'numpy_rng': digest([np.random.get_state()[0], np.random.get_state()[1].tolist(),
                                  *np.random.get_state()[2:]])}
    if game == 'race':
        state['car'] = {k: getattr(g.car, k) for k in ('position', 'speed', 'direction', 'k_left', 'k_right', 'k_up', 'k_down', 'MAX_FORWARD_SPEED', 'MAX_REVERSE_SPEED')}
        state.update(car_rect=list(g.car.rect), trophy_rect=list(g.trophy.rect), win=g.win_condition,
                     trophy_count=len(g.trophy_group), pads=[list(p.rect) for p in g.pad_group])
    elif game == 'flappybird':
        state.update(bird=list(g.bird_rect), pipes=[{'rect': list(p['rect']), 'counted': p['counted']} for p in g.pipe_list])
        state['animation'] = {k: getattr(g, k) for k in ('bird_movement', 'create_pipe_count', 'bird_flip_count', 'bird_index', 'floor_x_pos')}
    elif game == 'pong':
        state.update(ball=list(g.ball), paddleA=list(g.paddleA), paddleB=list(g.paddleB),
                     dx=g.ball_dx, dy=g.ball_dy, scoreA=g.scoreA, scoreB=g.scoreB)
    elif game == 'supermario':
        m = g.mario
        state.update(mario=list(m.rect), vel=[m.vel.x, m.vel.y], camera=[m.camera.x, m.camera.y],
                     flags={k: getattr(m, k) for k in ('restart', 'inAir', 'inJump', 'onGround', 'obeyGravity', 'powerUpState', 'invincibilityFrames')},
                     dashboard={k: getattr(g.dashboard, k) for k in ('points', 'coins', 'ticks', 'time')},
                     entities=[{'type': type(e).__name__, 'rect': list(e.rect),
                                'flags': {k: getattr(e, k) for k in ('alive', 'active', 'bouncing', 'triggered') if hasattr(e, k)}} for e in g.level.entityList])
    else:
        mode = g.current_mode
        level = mode.current_level
        state.update(player={k: getattr(mode.player, k) for k in ('x', 'y', 'z', 'lane', 'speed', 'dy', 'last_z_pos', 'current_mode', '_last_mode_before_death')},
                     loaded=level._currently_loaded_cell_range,
                     obstacles=[{'key': list(key), 'type': type(obs).__name__, 'lane': obs.lane,
                                 'z': obs.z, 'length': obs.length, 'dead': obs._is_dead,
                                 'jump': obs._can_jump, 'slide': obs._can_slide_through,
                                 'run': obs._can_run_through} for key, obs in sorted(level._obstacle_grid.items())])
    # JSON round-trip makes tuples/numpy scalar representation uniform.
    return json.loads(json.dumps(state, sort_keys=True, allow_nan=False))


def pixels(surface):
    import pygame
    return hashlib.sha256(pygame.image.tostring(surface, 'RGB')).hexdigest()


def screen_from_observation(observation):
    from PIL import Image
    assert set(observation) == {'image_png_base64'}, observation.keys()
    with Image.open(io.BytesIO(base64.b64decode(observation['image_png_base64'], validate=True))) as image:
        return {'size': list(image.size), 'pixels': hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()}


def baseline_setup(game, scratch):
    source = Path(os.environ.get('VMAGE_ROOT', '/opt/vmage')).resolve()
    for name in ('game', 'utils', 'config', 'res'):
        (scratch / name).symlink_to(source / name, target_is_directory=True)
    sys.dont_write_bytecode = True
    os.chdir(scratch)
    sys.path.insert(0, str(scratch))
    if game == 'supermario':
        sys.path.append(str(scratch / 'game/supermario'))
    os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
    random.seed(0)
    import numpy as np
    np.random.seed(0)
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))
    from utils.config import Config
    c = Config()
    c.load_env_config(str(scratch / f'config/env_config/3steps/env_config_{game}_reasoning_3steps.json'))
    c.load_level_config(str(scratch / f"config/level_config/{game}game/level{int(os.environ.get('VMAGE_TEST_LEVEL', '1'))}.json"))
    class Progress:
        def set_postfix(self, **kwargs):
            pass
    c.pbar = Progress()
    c.now_avg_score = 0
    return getattr(importlib.import_module('game.' + game + '_game'), CLASSES[game])


def worker(mode, game, actions, destination):
    sys.path.insert(0, str(RUNTIME))
    sys.path.insert(0, str(ROOT / 'game_first_exam/benchmarks/vmage/common'))
    register_schemas()
    calls = []
    constructed = []
    initial = []
    patched = set()
    original_import = importlib.import_module

    def instrument(cls):
        if cls in patched:
            return
        patched.add(cls)
        original_init, original_step = cls.__init__, cls.step
        def init(self, *a, **kw):
            constructed.append(1)
            if mode == 'construction-fault':
                raise RuntimeError('injected native construction failure')
            return original_init(self, *a, **kw)
        def step(self, action, dt=None):
            if mode == 'step-fault' and action != 'None':
                raise RuntimeError('injected native execution failure')
            result = original_step(self, action, dt)
            calls.append({'action': action, 'dt': dt, 'result': list(result),
                          'state': native_state(self, game), 'pixels': pixels(self.screen)})
            return result
        cls.__init__, cls.step = init, step

    def importing(name, *a, **kw):
        result = original_import(name, *a, **kw)
        if name == 'game.' + game + '_game':
            instrument(getattr(result, CLASSES[game]))
        return result

    with tempfile.TemporaryDirectory(prefix='vmage-test-') as td, patch.object(importlib, 'import_module', importing):
        scratch = Path(td)
        if mode == 'native':
            cls = baseline_setup(game, scratch)
            output = scratch / 'screens'
            output.mkdir()
            g = cls(str(output))
            class Complete(Exception):
                pass
            queue = iter(actions)
            def event_source():
                if not initial:
                    initial.append({'state': native_state(g, game), 'pixels': pixels(g.screen),
                                    'observation': screen_from_observation({'image_png_base64': g.last_frame_base64})})
                try:
                    return [next(queue)]
                except StopIteration:
                    raise Complete()
            # Upstream run is unchanged; this only supplies the human input.
            g.human_mode_action = lambda event: event
            import pygame
            with patch.object(pygame.event, 'get', event_source):
                try:
                    g.run(None, human_mode=True)
                except Complete:
                    pass
            result = {'constructed': len(constructed), 'calls': calls, 'initial': initial[0],
                      'final': native_state(g, game), 'pixels': pixels(g.screen),
                      'observation': screen_from_observation({'image_png_base64': g.last_frame_base64})}
            pygame.quit()
        else:
            task = task_for(game)
            instance = json.loads((task / 'tests/instance.json').read_text())
            adapter_module = module('tested_vmage_adapter', ROOT / f'game_first_exam/benchmarks/vmage/{game}/adapter.py')
            if mode == 'construction-fault':
                from server import Game
                from grade import grade
                rules = module('tested_fault_rules', ROOT / f'game_first_exam/benchmarks/vmage/{game}/metric_rules.py')
                service = Game.open(adapter_module.Adapter, instance, task / 'environment/sim', scratch / 'fault')
                verdict = grade(service.final, instance, rules.validate_metrics)
                assert verdict['infra_error'] == 1 and verdict['primary_score'] is None
                assert service.final['error']['phase'] == 'construction'
                assert len(constructed) == 1 and not calls
                Path(destination).write_text(json.dumps(verdict))
                service.close()
                return
            adapter = adapter_module.Adapter(instance, task / 'environment/sim')
            g = adapter.env
            initial.append({'state': native_state(g, game), 'pixels': pixels(g.screen),
                            'observation': screen_from_observation(adapter.observe())})
            assert len(constructed) == 1, 'observe actual native constructor, not a self-reported counter'
            assert len(calls) == 1 and calls[0]['action'] == 'None' and calls[0]['dt'] == 0
            assert len(g.game_frames) == 1
            try:
                adapter_module.Adapter(instance, task / 'environment/sim')
                raise AssertionError('second native construction accepted')
            except RuntimeError:
                pass
            assert len(constructed) == 1 and len(calls) == 1
            identity = id(g)
            def assert_pure():
                before = native_state(g, game)
                before_pixels = pixels(g.screen)
                before_fingerprint = adapter.fingerprint()
                before_calls = len(calls)
                observation = adapter.observe()
                frame = adapter.frame().copy()
                # Native draw/render can mutate collision state or generate RNG.
                owner, name = (g.current_mode, 'draw_to_screen') if game == 'tempestrun' else (g, 'render') if game == 'race' else (None, None)
                def queries():
                    for _ in range(3):
                        adapter.spec(); adapter.metrics(); adapter.success()
                        assert adapter.observe() == observation
                        assert (adapter.frame() == frame).all()
                        assert adapter.fingerprint() == before_fingerprint
                if owner is not None:
                    with patch.object(owner, name, side_effect=AssertionError('query rendered native game')):
                        queries()
                else:
                    queries()
                leaked_frame = adapter.frame()
                leaked_frame[0, 0] ^= 255
                assert (adapter.frame() == frame).all(), 'frame must not expose writable cache'
                assert native_state(g, game) == before
                assert pixels(g.screen) == before_pixels
                assert len(calls) == before_calls
            assert_pure()
            from server import Game
            from grade import grade
            rules = module('tested_vmage_rules', ROOT / f'game_first_exam/benchmarks/vmage/{game}/metric_rules.py')
            service_instance = copy.deepcopy(instance)
            assert instance['initial_state_sha256'] == adapter.fingerprint(), 'frozen initial audit hash mismatch'
            service = Game(adapter, service_instance, scratch / 'service', wall_clock=600)
            assert service.final is None
            if mode == 'step-fault':
                from server import EnvironmentFault
                try:
                    service.submit({'action': actions[0], 'expected_step': 0, 'request_id': 'fault'})
                    raise AssertionError('native failure accepted')
                except EnvironmentFault:
                    pass
                verdict = grade(service.final, service_instance, rules.validate_metrics)
                assert verdict['infra_error'] == 1 and verdict['primary_score'] is None
                assert service.final['error']['phase'] == 'step'
                assert service.final['metrics'] is None and service.final['success'] is None
                assert len(constructed) == 1 and len(calls) == 1
                Path(destination).write_text(json.dumps(verdict))
                service.close()
                return
            before = native_state(g, game)
            for body in ({'action': 'reset', 'expected_step': 0, 'request_id': 'illegal'},
                         {'action': actions[0], 'expected_step': 1, 'request_id': 'stale'}):
                try:
                    service.submit(body)
                    raise AssertionError('invalid/stale action accepted')
                except ValueError:
                    pass
                assert native_state(g, game) == before
            transitions = []
            for i, action in enumerate(actions):
                if g.over:
                    break
                body = {'action': action, 'expected_step': service.steps, 'request_id': 'native-' + str(i)}
                response = service.submit(body)
                assert service.final is None or not service.final.get('sim_error'), service.final
                transitions.append({'terminated': service.terminated, 'truncated': service.truncated})
                after = native_state(g, game)
                assert service.submit(body) == response
                assert native_state(g, game) == after, 'retry advanced native state/RNG'
                changed = dict(body, action=next(x for x in g.valid_actions if x != action))
                try:
                    service.submit(changed)
                    raise AssertionError('request ID collision accepted')
                except ValueError:
                    pass
                assert native_state(g, game) == after
                assert id(adapter.env) == identity, 'no reconstruction/reset'
                assert_pure()
            assert adapter.metrics()['native_step_calls'] == len(calls)
            assert adapter.metrics()['native_frame_count'] == len(g.game_frames)
            assert adapter.metrics()['decision_count'] == service.steps
            assert abs(service.reward - g.score) < 1e-9
            assert adapter.success() == (bool(g.win_condition) if game == 'race' else g.score > 0)
            result = {'constructed': len(constructed), 'calls': copy.deepcopy(calls), 'initial': initial[0],
                      'final': native_state(g, game), 'pixels': pixels(g.screen),
                      'observation': screen_from_observation(adapter.observe()),
                      'frame_pixels': hashlib.sha256(adapter.frame().tobytes()).hexdigest(),
                      'metrics': adapter.metrics(), 'transitions': transitions}
            before = native_state(g, game)
            if service.final is None:
                with patch('server.time.monotonic', return_value=1000.0):
                    service.started = 399.0
                    assert service.observe()['done']
                assert service.final['reason'] == 'time_limit'
            assert native_state(g, game) == before
            try:
                service.submit({'action': actions[0], 'expected_step': service.steps, 'request_id': 'after-final'})
                raise AssertionError('terminal action accepted')
            except ValueError:
                pass
            assert native_state(g, game) == before
            if g.over:
                try:
                    adapter.step(actions[0])
                    raise AssertionError('terminal native action accepted')
                except ValueError:
                    pass
                assert native_state(g, game) == before
            if game == 'tempestrun':
                cached = adapter.observe()
                cached_frame = adapter.frame().copy()
                time.sleep(.06)
                assert adapter.observe() == cached
                assert (adapter.frame() == cached_frame).all()
                assert native_state(g, game) == before
            valid = grade(service.final, service_instance, rules.validate_metrics)
            assert valid['infra_error'] == 0, valid
            assert valid['primary_score'] == g.score, valid
            mutations = [('native_score', -1), ('native_score', g.score + 1),
                         ('native_step_calls', 0), ('native_frame_count', -1),
                         ('native_initialization_calls', 2), ('initial_native_score', 1),
                         ('decision_count', service.steps + 1)]
            decomposition = {'race': ('native_win', not bool(getattr(g, 'win_condition', False))),
                             'flappybird': ('pipe_pair_score', g.score + 1),
                             'pong': ('score_a', g.score + 1),
                             'supermario': ('dashboard_points', g.score + 1),
                             'tempestrun': ('distance_z', g.score + 100)}[game]
            mutations.append(decomposition)
            if game == 'supermario':
                mutations.extend([('dashboard_ticks', (g.dashboard.ticks + 1) % 60),
                                  ('dashboard_time', g.dashboard.time + 1)])
            for field, value in mutations:
                altered = copy.deepcopy(service.final)
                altered['metrics'][field] = value
                try:
                    grade(altered, service_instance, rules.validate_metrics)
                    raise AssertionError('metric fault accepted: ' + field)
                except ValueError:
                    pass
            service.close()
        Path(destination).write_text(json.dumps(result, sort_keys=True, allow_nan=False))


class VMageNative(unittest.TestCase):
    def run_episode(self, mode, game, actions):
        with tempfile.TemporaryDirectory(prefix='vmage-result-') as td:
            output = Path(td) / 'result.json'
            run = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker', mode, game,
                                  json.dumps(actions), str(output)], cwd=ROOT, text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=int(os.environ.get("VMAGE_TEST_PROCESS_TIMEOUT", "90")))
            self.assertEqual(run.returncode, 0, run.stdout[-2000:] + run.stderr[-6000:])
            return json.loads(output.read_text())

    def assert_equivalent(self, game, actions, score=None):
        native = self.run_episode('native', game, actions)
        bridge = self.run_episode('bridge', game, actions)
        for key in ('constructed', 'initial', 'calls', 'final', 'pixels', 'observation'):
            self.assertEqual(bridge[key], native[key], game + ': ' + key)
        self.assertEqual(bridge['constructed'], 1)
        self.assertEqual(bridge['frame_pixels'], native['pixels'])
        self.assertEqual(native['calls'][0]['dt'], 0)
        self.assertTrue(all(c['dt'] == .033 for c in native['calls'][1:]))
        if score is not None:
            self.assertEqual(bridge['final']['score'], score)
        return bridge

    def test_original_native_run_positive_references(self):
        for game in GAMES:
            with self.subTest(game=game):
                self.assertEqual(json.loads((task_for(game) / 'solution/actions.json').read_text()), REFERENCES[game])
                result = self.assert_equivalent(game, REFERENCES[game], EXPECTED_SCORE[game])
                self.assertEqual(result['initial']['state']['score'], 0)
                self.assertEqual(result['initial']['state']['ledger'], 1)
                self.assertEqual(result['initial']['observation']['size'], [202 if game == 'flappybird' else 480, 360])
                if game == 'race':
                    self.assertEqual(result['final']['ledger'], 11)
                    self.assertEqual(len(result['calls']), 12)
                    self.assertEqual(result['transitions'][-1], {'terminated': True, 'truncated': False})
                    self.assertNotEqual(result['calls'][-1]['pixels'], result['calls'][-2]['pixels'])
                else:
                    self.assertFalse(result['final']['over'], 'positive score is auxiliary, not termination')

    def test_fresh_process_same_seed_preserves_state_rng_and_pixels(self):
        for game in GAMES:
            with self.subTest(game=game):
                first = self.run_episode('bridge', game, REFERENCES[game][:2])
                second = self.run_episode('bridge', game, REFERENCES[game][:2])
                for key in ('initial', 'calls', 'final', 'pixels', 'observation'):
                    self.assertEqual(first[key], second[key], game + ': ' + key)

    def test_native_screenshot_cap_boundary(self):
        for game, actions, ledger, calls in [('race', ['LEFT', 'RIGHT'] * 17, 101, 101),
                                            ('supermario', ['NONE'] * 80, 400, 401)]:
            with self.subTest(game=game):
                result = self.assert_equivalent(game, actions, 0)
                self.assertEqual(result['final']['ledger'], ledger)
                self.assertEqual(len(result['calls']), calls)
                self.assertEqual(result['transitions'][-1], {'terminated': False, 'truncated': True})
                if game == 'supermario':
                    self.assertEqual(result['metrics']['dashboard_ticks'], calls % 60)

    def test_native_death_preserves_accumulated_positive_score(self):
        result = self.assert_equivalent('flappybird', REFERENCES['flappybird'] + ['DOWN'] * 30, 1)
        self.assertTrue(result['final']['over'])
        self.assertEqual(result['transitions'][-1], {'terminated': True, 'truncated': False})
        self.assertGreater(result['metrics']['native_score'], 0)

    def test_tempest_native_death_and_wallclock_cache(self):
        actions = ['NONE'] * 100
        native = self.run_episode('native', 'tempestrun', actions)
        bridge = self.run_episode('bridge', 'tempestrun', actions)
        self.assertTrue(bridge['final']['over'])
        self.assertEqual(bridge['final']['player']['current_mode'], 'dead')
        self.assertGreater(bridge['final']['score'], 0)
        self.assertEqual(bridge['final'], native['final'])
        self.assertEqual(bridge['initial'], native['initial'])
        # Death effects use native real time. Compare physical/RNG state and
        # call/ledger boundaries independently from those visual timestamps.
        self.assertEqual([{k: v for k, v in c.items() if k != 'pixels'} for c in bridge['calls']],
                         [{k: v for k, v in c.items() if k != 'pixels'} for c in native['calls']])
        self.assertEqual(bridge['transitions'][-1], {'terminated': True, 'truncated': False})

    def test_tempest_passive_frames_use_none(self):
        result = self.assert_equivalent('tempestrun', ['LEFT', 'JUMP', 'RISE'])
        self.assertEqual([c['action'] for c in result['calls']], ['None', 'LEFT', 'NONE', 'NONE', 'JUMP', 'NONE', 'NONE', 'RISE', 'NONE', 'NONE'])
        self.assertEqual(result['final']['player']['lane'], -1)

    def test_native_engine_faults_remain_invalid_results(self):
        for mode in ('construction-fault', 'step-fault'):
            with self.subTest(mode=mode):
                result = self.run_episode(mode, 'race', ['RIGHT'])
                self.assertEqual(result['infra_error'], 1)
                self.assertIsNone(result['primary_score'])

    def test_source_and_assets_fail_closed(self):
        loader = module('_tested_source_loader', ROOT / 'game_first_exam/benchmarks/vmage/common/source_loader.py')
        metadata = loader.manifest()
        source = Path(os.environ.get('VMAGE_ROOT', '/opt/vmage')).resolve()
        loader.verify_source(source, metadata)
        with tempfile.TemporaryDirectory(prefix='vmage-source-test-') as td:
            scratch = Path(td)
            for relative in metadata['files']:
                path = scratch / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(source / relative)
            loader.verify_source(scratch, metadata)
            representatives = ['game/race_game.py', 'config/level_config/racegame/level1.json']
            representatives.append(next(p for p in metadata['files'] if p.endswith('.png')))
            for relative in representatives:
                with self.subTest(source=relative):
                    path = scratch / relative
                    path.unlink()
                    path.write_bytes(b'corrupt-native-payload')
                    with self.assertRaises(ValueError):
                        loader.verify_source(scratch, metadata)
                    path.unlink()
                    path.symlink_to(source / relative)
            for field in ('upstream_commit', 'archive_sha256', 'source_manifest_sha256'):
                altered = copy.deepcopy(metadata)
                altered[field] = '0' * 64
                with self.subTest(provenance=field), self.assertRaises(ValueError):
                    loader.verify_source(source, altered)

    def test_strict_schemas_without_native_import(self):
        sys.path.insert(0, str(RUNTIME))
        register_schemas()
        from config_schema import validate_instance
        self.assertNotIn('pygame', sys.modules)
        for game in GAMES:
            instance = json.loads((task_for(game) / 'tests/instance.json').read_text())
            validate_instance(instance)
            faults = [dict(instance, unknown_native_option=True), dict(instance, seed=True),
                      dict(instance, seed=1), dict(instance, max_steps=100),
                      dict(instance, observation_profile='native-rgb-v1'), dict(instance, env_id='arbitrary-module')]
            schema = sys.modules['_test_vmage_' + game + '_schema']
            for field, expected in schema.FROZEN_FIELDS.items():
                changed = copy.deepcopy(instance)
                if type(expected) is str:
                    changed[field] = expected + '-changed'
                elif type(expected) in (int, float):
                    changed[field] = expected + 1
                elif type(expected) is dict:
                    changed[field][next(iter(expected))] += '-changed'
                elif type(expected) is list:
                    changed[field][0] = changed[field][0] + '-changed' if isinstance(changed[field][0], str) else changed[field][0] + 1
                else:
                    changed[field] = 'unfrozen-value'
                faults.append(changed)
            for changed in faults:
                with self.subTest(game=game, fields=[k for k in changed if changed.get(k) != instance.get(k)]):
                    with self.assertRaises(ValueError):
                        validate_instance(changed)
        self.assertNotIn('pygame', sys.modules, 'configuration validation must remain stdlib-only')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--worker':
        worker(sys.argv[2], sys.argv[3], json.loads(sys.argv[4]), sys.argv[5])
    else:
        unittest.main()
