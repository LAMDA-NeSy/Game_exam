"""Compare the pixel adapter with the pinned native engine and its verifier."""

import json
from pathlib import Path
import sys
import unittest

import numpy as np
from slimevolleygym.slimevolley import SlimeVolleyAtariEnv

GAME = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GAME / "benchmarks/slimevolley"), str(GAME / "runtime")]
from adapter import Adapter
from config_schema import register_instance_schema, validate_instance
import instance_schema
from metric_rules import validate_metrics

TASK = GAME / "tasks/slimevolley/slimevolley-pixel-vs-baseline-i01-standard"
ACTION_INDEX = {"idle": 0, "left": 1, "left_jump": 2, "jump": 3, "right_jump": 4, "right": 5}


class SlimeVolleyNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        register_instance_schema(instance_schema)
        cls.instance = validate_instance(json.loads((TASK / "tests/instance.json").read_text()))

    def compare(self, actions, expected_steps, expected_score, ending):
        native = SlimeVolleyAtariEnv()
        self.addCleanup(native.close)
        native.seed(self.instance["seed"])
        match = Adapter(self.instance)
        self.addCleanup(match.close)
        initial = match.fingerprint()
        self.assertEqual(initial, self.instance["initial_state_sha256"])
        np.testing.assert_array_equal(match.frame(), native.reset())
        self.assertEqual(match.frame().shape, (84, 168, 3))
        self.assertEqual(match.frame().dtype, np.uint8)
        self.assertEqual(match.observe(), match.observe())
        self.assertEqual(set(match.observe()), {"image_png_base64"})
        self.assertEqual(match.fingerprint(), initial)
        self.assertEqual(match.spec()["action_schema"]["enum"], list(ACTION_INDEX))

        total = 0
        for step, action in enumerate(actions, 1):
            expected, reward, done, info = native.step(ACTION_INDEX[action])
            result = match.step(action)
            np.testing.assert_array_equal(match.frame(), expected)
            self.assertEqual(result.reward, reward)
            self.assertEqual(result.terminated or result.truncated, done)
            total += reward
            if done:
                break

        self.assertEqual((step, total), (expected_steps, expected_score))
        self.assertEqual((result.terminated, result.truncated), ending)
        self.assertEqual((match.metrics()["right_lives"], match.metrics()["left_lives"]),
                         (info["ale.lives"], info["ale.otherLives"]))
        final = {"steps": step, "return": total, "metrics": match.metrics(),
                 "terminated": result.terminated, "truncated": result.truncated,
                 "success": match.success()}
        validate_metrics(final, self.instance)
        self.assertEqual(match.success(), expected_score > 0)
        with self.assertRaises(ValueError):
            validate_metrics({**final, "return": total + 1}, self.instance)

    def test_reference_matches_native_to_frame_limit(self):
        actions = json.loads((TASK / "solution/actions.json").read_text())
        self.compare(actions, 3000, 1, (False, True))

    def test_idle_matches_native_to_life_exhaustion(self):
        self.compare(["idle"] * 3000, 557, -5, (True, False))

    def test_each_discrete_action_matches_native(self):
        for action, index in ACTION_INDEX.items():
            with self.subTest(action=action):
                native = SlimeVolleyAtariEnv()
                match = Adapter(self.instance)
                try:
                    native.seed(self.instance["seed"])
                    native.reset()
                    expected, reward, _, _ = native.step(index)
                    result = match.step(action)
                    np.testing.assert_array_equal(match.frame(), expected)
                    self.assertEqual(result.reward, reward)
                finally:
                    native.close()
                    match.close()


if __name__ == "__main__":
    unittest.main()
