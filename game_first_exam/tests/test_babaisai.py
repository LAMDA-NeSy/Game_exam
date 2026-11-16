"""Baba native equivalence, reproducibility, and the two independent budget boundaries."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'game_first_exam/runtime'), str(ROOT / 'game_first_exam/benchmarks/babaisai')]
sys.path.insert(0, str(ROOT / 'scripts'))
from game_schemas import register_schemas

register_schemas()
from adapter import ACTIONS, Adapter, baba, native_state
from baba.grid import BabaIsYouEnv, BabaIsYouGrid, put_rule
from baba.world_object import Baba, FBall, FWall, RuleProperty, Wall
from encoding import state_hash
from grade import grade
from metric_rules import validate_metrics
from server import Game


class BabaTests(unittest.TestCase):
    def pair(self, setup, budget=100):
        """Small native-engine boundary fixtures, never exported as benchmark tasks."""
        class BoundaryEnv(BabaIsYouEnv):
            def _gen_grid(self, width, height):
                self.grid = BabaIsYouGrid(width, height)
                self.grid.wall_rect(0, 0, width, height)
                setup(self)
        _, cfg = next(self.configs())
        cfg = {**cfg, 'native_max_steps': budget}
        raw = BoundaryEnv(width=8, height=8, max_steps=budget); raw.reset(seed=cfg['seed'])
        self.addCleanup(raw.close)
        with patch.object(baba, 'make', side_effect=lambda *a, **kw: BoundaryEnv(width=8, height=8, max_steps=budget)):
            adapter = Adapter(cfg)
        self.addCleanup(adapter.close)
        return raw, adapter

    def equivalent_step(self, raw, adapter, action):
        _, reward, done, _ = raw.step(ACTIONS[action]); transition = adapter.step(action)
        self.assertEqual(reward, transition.reward)
        self.assertEqual(bool(done), transition.terminated or transition.truncated)
        self.assertEqual(state_hash(native_state(raw)), adapter.fingerprint())
        return transition

    def configs(self):
        for task in sorted((ROOT / 'game_first_exam/tasks/babaisai').glob('*-standard')):
            yield task, json.loads((task / 'tests/instance.json').read_text())

    def test_same_seed_reproduces_and_different_seeds_change_state(self):
        for task, cfg in self.configs():
            states = []
            for seed in [cfg['seed'], cfg['seed'], 1056882141, 470363396]:
                a = Adapter({**cfg, 'seed': seed}); states.append(a.fingerprint()); a.close()
            self.assertEqual(states[0], states[1], task.name)
            self.assertEqual(states[0], cfg['initial_state_sha256'])
            self.assertGreater(len(set(states)), 1)

    def test_reference_actions_match_unwrapped_native_engine(self):
        for task, cfg in self.configs():
            raw = baba.make(cfg['env_id'], max_steps=cfg['native_max_steps']); raw.reset(seed=cfg['seed'])
            a = Adapter(cfg)
            try:
                for action in json.loads((task / 'solution/actions.json').read_text()):
                    self.equivalent_step(raw, a, action)
                self.assertTrue(a.success())
            finally:
                a.close(); raw.close()

    def test_native_truncation_and_public_limit_remain_distinct(self):
        _, base = next(self.configs())
        for native, public, reason in [(2, 4, 'native_truncated'), (100, 2, 'step_limit')]:
            cfg = copy.deepcopy(base); cfg.update(native_max_steps=native, max_steps=public)
            factory = baba.make
            with patch.object(baba, 'make', side_effect=lambda env_id, factory=factory, native=native: factory(env_id, max_steps=native)):
                a = Adapter(cfg)
            cfg['initial_state_sha256'] = a.fingerprint()
            with tempfile.TemporaryDirectory() as out:
                g = Game(a, cfg, out)
                try:
                    for i in range(2): g.submit({'action': 'idle', 'expected_step': i, 'request_id': str(i)})
                    self.assertEqual(g.final['reason'], reason)
                    self.assertEqual(g.final['truncated'], native == 2)
                    self.assertEqual(grade(g.final, cfg, validate_metrics)['infra_error'], 0)
                finally: g.close()

    def test_observation_is_only_native_rendering(self):
        def setup(e):
            put_rule(e, 'baba', 'you', (1, 1)); e.put_obj(Baba(), 2, 4)
            e.put_obj(Wall(), 4, 4); e.put_obj(FWall(), 5, 4)
        _, a = self.pair(setup)
        before = a.fingerprint()
        self.assertEqual(set(a.observe()), {'image_png_base64'})
        import base64

        import cv2
        import numpy as np
        decoded = cv2.cvtColor(cv2.imdecode(np.frombuffer(base64.b64decode(a.observe()['image_png_base64']), np.uint8), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        np.testing.assert_array_equal(decoded, a.env.render(mode='rgb_array', tile_size=32))
        self.assertEqual(before, a.fingerprint())

    def test_break_you_rule_preserves_native_nonterminal_state(self):
        def setup(e):
            put_rule(e, 'baba', 'you', (1, 2)); e.put_obj(Baba(), 2, 3)
        raw, a = self.pair(setup)
        self.equivalent_step(raw, a, 'up')
        self.assertFalse(a.env._ruleset['is_agent'].get('baba', False))
        positions = lambda e: [(i, type(o).__name__) for i, stack in enumerate(e.grid.grid) for o in stack if isinstance(o, Baba)]
        before = positions(a.env)
        for action in ['right', 'down', 'left']:
            t = self.equivalent_step(raw, a, action)
            self.assertFalse(t.terminated or t.truncated)
        self.assertEqual(before, positions(a.env))

    def test_word_pushed_into_corner_stays_blocked(self):
        def setup(e):
            put_rule(e, 'baba', 'you', (3, 5)); e.put_obj(Baba(), 1, 3)
            e.put_obj(RuleProperty('win'), 1, 2)
        raw, a = self.pair(setup)
        for action in ['up', 'up', 'left']:
            self.equivalent_step(raw, a, action)
        self.assertEqual(a.env.grid.get(1, 1).property, 'is_goal')
        self.assertEqual(tuple(a.env.agent_pos), (1, 2))

    def test_overlap_then_separate_preserves_hidden_stack_and_fingerprint(self):
        def setup(e):
            put_rule(e, 'baba', 'you', (1, 1)); e.put_obj(Baba(), 2, 4); e.put_obj(FBall(), 3, 4)
        raw, a = self.pair(setup)
        self.equivalent_step(raw, a, 'right')
        stack = [o for o in a.env.grid.get(3, 4, 'all') if o is not None]
        self.assertEqual([type(o).__name__ for o in stack], ['FBall', 'Baba'])
        before = a.fingerprint(); visible = a.env.grid.encode().copy()
        stack[0].color = 'red'
        self.assertNotEqual(before, a.fingerprint())
        self.assertTrue((visible == a.env.grid.encode()).all())
        stack[0].color = 'green'
        self.equivalent_step(raw, a, 'left')
        self.assertIsInstance(a.env.grid.get(3, 4), FBall)

    def test_colored_native_rules_hash_and_read_without_side_effects(self):
        def setup(e):
            put_rule(e, 'baba', 'you', (1, 1)); put_rule(e, ('blue', 'ball'), 'win', (1, 2))
            e.put_obj(Baba(), 2, 4); e.put_obj(FBall(color='red'), 3, 4)
        raw, a = self.pair(setup)
        self.assertEqual(a.env._ruleset['is_goal']['fball_color'], {'blue'})
        before = a.fingerprint(); a.observe(); a.spec(); a.frame()
        self.assertEqual(before, a.fingerprint())
        self.equivalent_step(raw, a, 'right')
        self.assertFalse(a.success())

    def test_win_on_last_native_and_public_step_preserves_both_flags(self):
        task, cfg = next((t, c) for t, c in self.configs() if c['env_id'] == 'env/goto_win')
        actions = json.loads((task / 'solution/actions.json').read_text())
        cfg = {**cfg, 'native_max_steps': len(actions), 'max_steps': len(actions)}
        raw = baba.make(cfg['env_id'], max_steps=len(actions)); raw.reset(seed=cfg['seed'])
        self.addCleanup(raw.close)
        factory = baba.make
        with patch.object(baba, 'make', side_effect=lambda env_id: factory(env_id, max_steps=len(actions))):
            a = Adapter(cfg)
        cfg['initial_state_sha256'] = a.fingerprint()
        with tempfile.TemporaryDirectory() as out:
            g = Game(a, cfg, out)
            try:
                for action in actions:
                    _, reward, done, _ = raw.step(ACTIONS[action])
                    g.submit({'action': action, 'expected_step': g.steps, 'request_id': str(g.steps)})
                    self.assertEqual(state_hash(native_state(raw)), a.fingerprint())
                self.assertTrue(done)
                self.assertAlmostEqual(reward, .1)
                self.assertTrue(g.final['terminated'] and g.final['truncated'] and g.final['budget_exhausted'])
                self.assertEqual(g.final['reason'], 'native_terminated')
                self.assertEqual(grade(g.final, cfg, validate_metrics)['success'], 1)
            finally: g.close()


if __name__ == '__main__': unittest.main()
