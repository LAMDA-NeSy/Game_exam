"""Real MiniHack/NLE comparisons using the pinned, unmodified upstream engines."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import gymnasium as gym
import numpy as np
from minihack.envs import boxohack

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'game_first_exam/runtime'),
               str(ROOT / 'game_first_exam/benchmarks/minihack')]
from adapter import Adapter
from game_schemas import register_schemas
from grade import grade
from metric_rules import validate_metrics
from server import Game

register_schemas()
TASK_ROOT = ROOT / 'game_first_exam/tasks/minihack'
TASKS = sorted(TASK_ROOT.glob('*-standard'))
ROOM = TASK_ROOT / 'minihack-room-i01-standard'
RIVER = TASK_ROOT / 'minihack-river-i01-standard'
CROP_KEYS = {'glyphs_crop', 'chars_crop', 'colors_crop', 'specials_crop', 'blstats', 'message'}
NATIVE_KEYS = CROP_KEYS | {'glyphs', 'chars', 'colors', 'specials'}
INVENTORY_KEYS = {'inv_letters', 'inv_strs'}
PUBLIC_KEYS = {
    'native-observation-v1': NATIVE_KEYS,
    'player-crop-9x9-v1': CROP_KEYS,
    'player-crop-inventory-9x9-v1': CROP_KEYS | INVENTORY_KEYS,
}


def instance(task):
    return json.loads((task / 'tests/instance.json').read_text())


def native(config, assets=None):
    if config['family'].startswith('boxoban-'):
        with patch.object(boxohack, 'LEVELS_PATH', assets / 'boxoban'):
            env = gym.make(config['env_id'], disable_env_checker=True)
        env.unwrapped._goal_pos_set = frozenset()
        env.unwrapped.seed(config['seed'], config['seed'], reseed=False)
        obs, info = env.reset()
        return env, obs, info
    env = gym.make(config['env_id'])
    env.unwrapped.seed(config['seed'], config['seed'], reseed=False)
    obs, info = env.reset(seed=config['seed'])
    return env, obs, info


class MiniHackNative(unittest.TestCase):
    def test_native_calendar_is_fixed_but_budget_clock_is_real(self):
        self.assertEqual(time.strftime('%Y-%m-%d', time.gmtime()), '2026-11-13')
        # RAW is not virtualized by libfaketime; a fake epoch-valued monotonic clock
        # would break service deadlines even if the initial game hash matched.
        self.assertLess(abs(time.monotonic() - time.clock_gettime(time.CLOCK_MONOTONIC_RAW)), 600)
        start = time.monotonic()
        time.sleep(.03)
        self.assertGreaterEqual(time.monotonic() - start, .02)

    def test_native_real_world_calendar_changes_initial_state(self):
        config = instance(RIVER)
        program = f'''import gymnasium as gym, minihack, json
e=gym.make({config['env_id']!r})
e.unwrapped.seed({config['seed']}, {config['seed']}, reseed=False)
o,_=e.reset(seed={config['seed']})
print(json.dumps({{'message': bytes(o['message']).split(b'\\0')[0].decode()}}))
e.close()
'''
        messages = []
        for date in ('2026-11-12', '2026-11-13', '2026-11-15'):
            env = dict(os.environ, FAKETIME='@' + date + ' 12:00:00')
            output = subprocess.check_output([sys.executable, '-c', program], env=env, text=True)
            messages.append(json.loads(output)['message'])
        self.assertIn('New moon', messages[0])
        self.assertIn('Friday the 13th', messages[1])
        self.assertIn('welcome', messages[2])

    def test_unpinned_clock_is_rejected(self):
        with patch.dict(os.environ, {'FAKETIME': '@2026-11-15 12:00:00'}):
            with self.assertRaisesRegex(ValueError, 'calendar clock mismatch'):
                Adapter(instance(ROOM))

    def test_reference_matches_native_at_every_step_and_keeps_defaults(self):
        for task in TASKS:
            config = instance(task)
            with self.subTest(task=task.name):
                assets = task / 'environment/sim'
                adapter = Adapter(config, assets)
                env, obs, info = native(config, assets)
                try:
                    raw = env.unwrapped
                    self.assertEqual(adapter.fingerprint(), config['initial_state_sha256'])
                    self.assertEqual(adapter.env.unwrapped.get_seeds(), (config['seed'], config['seed'], False))
                    self.assertEqual(raw._max_episode_steps, config['native_max_steps'])
                    if task in {ROOM, RIVER}:
                        self.assertEqual((raw.reward_win, raw.reward_lose, raw.penalty_mode,
                                          raw.penalty_step, raw.penalty_time), (1, 0, 'constant', -.01, 0))
                        self.assertEqual((raw.character, raw._allow_all_modes, raw._allow_all_yn_questions),
                                         ('rog-hum-cha-mal', False, False))
                    self.assertEqual((raw.obs_crop_h, raw.obs_crop_w), (9, 9))
                    spec = adapter.spec()
                    if config['family'].startswith('quest-'):
                        self.assertEqual(set(spec['action_indices'].values()), set(range(len(raw.actions))))
                        self.assertEqual(spec['action_keys'], {
                            name: int(raw.actions[i]) for name, i in spec['action_indices'].items()
                        })
                        self.assertEqual((spec['action_keys']['E'], spec['action_keys']['RUN_E']),
                                         (ord('l'), ord('L')))
                        self.assertTrue(INVENTORY_KEYS <= obs.keys())
                    else:
                        self.assertEqual(spec['action_indices'], {a.name: i for i, a in enumerate(raw.actions)})
                        self.assertNotIn('action_keys', spec)
                        self.assertEqual(set(obs), NATIVE_KEYS)
                    keys = PUBLIC_KEYS[config['observation_profile']]
                    self.assertEqual(adapter.observe(), {key: obs[key].tolist() for key in keys})
                    reward_sum = 0
                    for action in json.loads((task / 'solution/actions.json').read_text()):
                        obs, reward, term, trunc, info = env.step(adapter.actions[action])
                        transition = adapter.step(action)
                        reward_sum += reward
                        self.assertEqual((transition.reward, transition.terminated, transition.truncated), (reward, term, trunc))
                        self.assertEqual(adapter.observe(), {key: obs[key].tolist() for key in keys})
                        for got, expected in zip(adapter.env.unwrapped.last_observation, raw.last_observation, strict=True):
                            np.testing.assert_array_equal(got, expected)
                        self.assertEqual(adapter.info, info)
                    self.assertTrue(adapter.success())
                    self.assertEqual(adapter.total_return, reward_sum)
                    if task in {ROOM, RIVER}:
                        self.assertEqual(reward_sum, 1.0)
                finally:
                    adapter.close(); env.close()

    def test_native_limit_and_negative_return_are_not_public_step_limit(self):
        config = instance(ROOM)
        env, _, _ = native(config)
        try:
            with tempfile.TemporaryDirectory() as out:
                adapter = Adapter(config)
                game = Game(adapter, config, out)
                reward_sum = 0
                for index in range(config['native_max_steps'] + 1):
                    if game.final is not None:
                        break
                    _, reward, term, trunc, info = env.step(adapter.actions['N'])
                    game.submit({'action': 'N', 'expected_step': index, 'request_id': str(index)})
                    reward_sum += reward
                    self.assertEqual(adapter.total_return, reward_sum)
                    self.assertEqual(adapter.ended, term or trunc)
                self.assertIsNotNone(game.final)
                self.assertEqual(game.steps, config['native_max_steps'])
                self.assertEqual((game.final['terminated'], game.final['truncated']), (term, trunc))
                self.assertEqual(game.final['end_source'], 'native')
                self.assertFalse(game.final['budget_exhausted'])
                self.assertEqual(adapter.metrics()['native_end_status'], int(info['end_status']))
                self.assertEqual(int(info['end_status']), -1)
                result = grade(game.final, config, validate_metrics)
                self.assertEqual(result['infra_error'], 0)
                self.assertEqual(result['primary_metric'], 'completion_score')
                self.assertEqual(result['primary_score'], 0)
                self.assertAlmostEqual(result['return'], -1.0)
                for field, value in [('native_end_status', 2), ('native_steps', 3), ('native_return', 1.0),
                                     ('completion_score', 100)]:
                    forged = copy.deepcopy(game.final)
                    forged['metrics'][field] = value
                    with self.assertRaises(ValueError):
                        grade(forged, config, validate_metrics)
                missing_score = copy.deepcopy(game.final)
                del missing_score['metrics']['completion_score']
                with self.assertRaisesRegex(ValueError, 'completion score'):
                    grade(missing_score, config, validate_metrics)
                game.close()
        finally:
            env.close()

    def test_observation_render_and_spec_do_not_advance_game_or_rng(self):
        config = instance(ROOM)
        first, second = Adapter(config), Adapter(config)
        try:
            actions = json.loads((ROOM / 'solution/actions.json').read_text())
            for action in actions:
                before = first.fingerprint()
                for _ in range(3):
                    first.observe(); first.frame(); first.spec()
                self.assertEqual(before, first.fingerprint())
                self.assertEqual(first.step(action), second.step(action))
                self.assertEqual(first.fingerprint(), second.fingerprint())
        finally:
            first.close(); second.close()

    def test_public_feedback_deduplication_and_last_step_match_native(self):
        task = ROOM
        config = instance(task)
        reference = json.loads((task / 'solution/actions.json').read_text())
        # Exercise a win with a lower native return and reaching the goal on the native limit.
        # NLE, not the adapter/grader, decides the latter's outcome and flags.
        for stalls in (3, config['native_max_steps'] - len(reference)):
            with self.subTest(stalls=stalls), tempfile.TemporaryDirectory() as out:
                env, initial, _ = native(config)
                game = Game(Adapter(config), config, out)
                try:
                    public_keys = {'observation', 'step', 'done', 'steps_remaining', 'time_left_s'}
                    self.assertEqual(game.spec()['observation_profile'], 'player-crop-9x9-v1')
                    start = game.observe()
                    self.assertEqual(set(start), public_keys)
                    self.assertEqual(start['observation'], {key: initial[key].tolist() for key in CROP_KEYS})
                    chars = start['observation']['chars_crop']
                    self.assertEqual([len(row) for row in chars], [9] * 9)
                    self.assertEqual(chars[4][4], ord('@'))
                    total = 0.0
                    for index, action in enumerate(['N'] * stalls + reference):
                        obs, reward, term, trunc, info = env.step(game.adapter.actions[action])
                        request = {'action': action, 'expected_step': index, 'request_id': str(index)}
                        response = game.submit(request)
                        total += reward
                        self.assertEqual(set(response), public_keys)
                        self.assertIsNone(response['steps_remaining'])
                        self.assertEqual(response['observation'], {key: obs[key].tolist() for key in CROP_KEYS})
                        self.assertEqual(response['done'], bool(term or trunc))
                        self.assertAlmostEqual(game.reward, total)
                        self.assertEqual((game.terminated, game.truncated), (bool(term), bool(trunc)))
                        for got, expected in zip(game.adapter.env.unwrapped.last_observation,
                                                 env.unwrapped.last_observation, strict=True):
                            np.testing.assert_array_equal(got, expected)
                        if index == 0:
                            # A retried stalled action must not incur a second penalty.
                            before = game.adapter.fingerprint()
                            self.assertEqual(game.submit(request), response)
                            self.assertEqual(game.adapter.fingerprint(), before)
                            self.assertEqual(game.steps, 1)
                            self.assertAlmostEqual(game.reward, reward)
                        if response['done']:
                            break
                    self.assertIsNotNone(game.final)
                    self.assertEqual(game.final['end_source'], 'native')
                    self.assertFalse(game.final['budget_exhausted'])
                    self.assertEqual(game.final['metrics']['native_end_status'], int(info['end_status']))
                    result = grade(game.final, config, validate_metrics)
                    self.assertAlmostEqual(result['return'], total)
                    self.assertEqual(result['success'], int(info['end_status'] == env.unwrapped.StepStatus.TASK_SUCCESSFUL))
                    if stalls == 3:
                        self.assertEqual(result['success'], 1)
                        self.assertEqual(result['primary_score'], 100)
                        self.assertAlmostEqual(total, .97)
                    else:
                        self.assertEqual(game.steps, config['native_max_steps'])
                        self.assertEqual(result['success'], 0)
                        self.assertEqual(result['primary_score'], 0)
                finally:
                    game.close()
                    env.close()

    def test_seed_reproduction_across_processes(self):
        for task in TASKS:
            program = f'''import json, sys
sys.path[:0] = {sys.path[:3]!r}
from adapter import Adapter
a = Adapter(json.load(open({str(task / 'tests/instance.json')!r})), {str(task / 'environment/sim')!r})
print(a.fingerprint())
a.close()
'''
            with self.subTest(task=task.name):
                for _ in range(2):
                    output = subprocess.check_output([sys.executable, '-c', program], text=True)
                    self.assertEqual(output.strip(), instance(task)['initial_state_sha256'])

    def test_source_and_engine_mismatch_rejected(self):
        config = instance(ROOM)
        config['engine_archive_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source archive mismatch'):
            Adapter(config)
        config = instance(ROOM)
        config['engine_versions']['nle'] = '0.0.0'
        with self.assertRaisesRegex(ValueError, 'version mismatch'):
            Adapter(config)


if __name__ == '__main__':
    unittest.main()
