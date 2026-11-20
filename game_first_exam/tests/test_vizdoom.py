"""Compare the isolated ViZDoom adapter with the installed native scenarios."""
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image
import vizdoom as vzd

GAME_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GAME_ROOT / "runtime"), str(GAME_ROOT / "benchmarks/vizdoom")]

from adapter import Adapter
from config_schema import register_instance_schema, validate_instance
from grade import grade
import instance_schema
from metric_rules import validate_metrics
from server import Game, InvalidAction
from vizdoom_actions import encode_action
from vizdoom_server import ViZDoomSession

register_instance_schema(instance_schema)


class ViZDoomTests(unittest.TestCase):
    def scenarios(self):
        for family in ("basic", "my-way-home"):
            spec = instance_schema.SCENARIOS[family]
            task = GAME_ROOT / "tasks/vizdoom" / f"vizdoom-{family}-i01-standard"
            instance = validate_instance(json.loads((task / "tests/instance.json").read_text()))
            actions = json.loads((task / "solution/actions.json").read_text())
            yield instance, spec, actions

    def native(self, instance, spec, directory):
        installed = Path(vzd.__file__).resolve().parent
        game = vzd.DoomGame()
        self.addCleanup(game.close)
        self.assertTrue(game.load_config(str(installed / "scenarios" / f"{spec['stem']}.cfg")))
        game.set_doom_game_path(str(installed / "freedoom2.wad"))
        game.set_doom_config_path(str(Path(directory) / "native.ini"))
        game.set_seed(instance["seed"])
        game.set_window_visible(False)
        game.set_sound_enabled(False)
        game.set_screen_format(vzd.ScreenFormat.RGB24)
        game.init()
        return game

    def compare(self, instance, spec, actions, expected):
        with tempfile.TemporaryDirectory() as directory:
            adapter = Adapter(instance, Path(directory))
            try:
                native = self.native(instance, spec, directory)
                try:
                    self.assertEqual(adapter.fingerprint(), instance["initial_state_sha256"])
                    self.assertEqual(len(adapter.spec()["actions"]), 2 ** len(spec["buttons"]))
                    self.assertEqual(native.get_episode_timeout(), spec["timeout_tics"])
                    self.assertEqual(native.get_episode_time(), spec["start_tic"])
                    for decision, (action, tics) in enumerate(actions, start=1):
                        buttons = action.split("+")
                        vector = [int(button in buttons) for button in spec["buttons"]]
                        reward = native.make_action(vector, tics)
                        wire_action = action if tics == 1 else f"{action}@{tics}"
                        transition = adapter.step(wire_action)
                        self.assertAlmostEqual(reward, transition.reward, places=10)
                        self.assertEqual(transition.terminated or transition.truncated, native.is_episode_finished())
                        self.assertEqual(transition.truncated, native.is_episode_timeout_reached())
                        self.assertEqual(adapter.action_tics[-1][0], tics)
                        if native.is_episode_finished():
                            self.assertEqual(decision, len(actions))
                            self.assertIsNone(adapter.frame())
                            self.assertEqual(adapter.observe(), {"frame_available": False})
                        else:
                            self.assertEqual(adapter.advanced_tics, native.get_episode_time() - spec["start_tic"])
                            self.assertTrue(np.array_equal(adapter.frame(), native.get_state().screen_buffer))
                    self.assertTrue(native.is_episode_finished())
                    self.assertAlmostEqual(adapter.metrics()["native_return"], native.get_total_reward(), places=10)
                    self.assertEqual(adapter.success(), expected)
                    self.assertEqual(adapter.truncated, not expected)
                    self.assertLess(adapter.action_tics[-1][1], actions[-1][1])
                    self.assertEqual(sum(actual for _, actual in adapter.action_tics), adapter.advanced_tics)
                    if not expected:
                        self.assertEqual(adapter.advanced_tics, spec["timeout_tics"])
                finally:
                    native.close()
            finally:
                adapter.close()

    def test_reference_and_native_timeout_match_batched_native_actions(self):
        for instance, spec, actions in self.scenarios():
            winning = [(actions[0], 1), (actions[0], 3)]
            winning += [(action, 4) for action in actions[1:-1]]
            winning.append((actions[-1], 16))
            timeout = [("noop", 1), ("noop", 16), ("noop", spec["timeout_tics"])]
            for expected, steps in ((True, winning), (False, timeout)):
                with self.subTest(family=instance["family"], objective=expected):
                    self.compare(instance, spec, steps, expected)

    def test_public_observation_and_invalid_or_repeated_action(self):
        import base64
        for instance, _, _ in self.scenarios():
            with self.subTest(family=instance["family"]), tempfile.TemporaryDirectory() as directory:
                game = Game.open(Adapter, instance, Path(directory), Path(directory) / "record")
                try:
                    self.assertIsNone(game.final)
                    snapshot = game.observe()
                    obs = snapshot["observation"]
                    self.assertEqual(set(obs), {"frame_available", "image_png_base64"})
                    image = Image.open(io.BytesIO(base64.b64decode(obs["image_png_base64"])))
                    self.assertEqual((image.mode, image.size), ("RGB", (320, 240)))
                    self.assertEqual(snapshot["observation"], game.observe()["observation"])
                    self.assertEqual(game.adapter.metrics()["native_tics"], 0)
                    self.assertEqual(game.spec()["reset_budget"], 0)
                    with self.assertRaises(InvalidAction):
                        game.submit({"action": "RESET", "expected_step": 0, "request_id": "bad"})
                    self.assertEqual(game.adapter.advanced_tics, 0)
                    self.assertEqual(game.spec()["default_tics"], 1)
                    for raw in ("noop@0", "noop@-1", "noop@1.5", "noop@true", "noop@4@4"):
                        with self.assertRaises(InvalidAction):
                            game.submit({"action": raw, "expected_step": 0, "request_id": raw})
                    self.assertEqual(game.adapter.advanced_tics, 0)
                    request = {"action": "noop", "expected_step": 0, "request_id": "one"}
                    self.assertEqual(game.submit(request), game.submit(request))
                    self.assertEqual(game.adapter.advanced_tics, 1)
                    with self.assertRaisesRegex(ValueError, "different payload"):
                        game.submit({**request, "action": "noop@16"})
                    request = {"action": "noop@16", "expected_step": 1, "request_id": "two"}
                    self.assertEqual(game.submit(request), game.submit(request))
                    self.assertEqual(game.adapter.advanced_tics, 17)
                    game.finalize("agent_finished")
                    verdict = grade(game.final, instance, validate_metrics)
                    self.assertTrue(verdict["result_valid"])
                    self.assertEqual(verdict["primary_score"], 0)
                    self.assertEqual(game.final["metrics"]["action_tics"], [[1, 1], [16, 16]])
                    damaged = {**game.final, "metrics": {**game.final["metrics"], "action_tics": [[1, 1], [17, 16]]}}
                    with self.assertRaisesRegex(ValueError, "action duration"):
                        grade(damaged, instance, validate_metrics)
                finally:
                    game.close()

    def test_no_action_is_valid_failure(self):
        for instance, _, _ in self.scenarios():
            with self.subTest(family=instance["family"]), tempfile.TemporaryDirectory() as directory:
                game = Game.open(Adapter, instance, Path(directory), Path(directory) / "record")
                try:
                    game.finalize("agent_finished")
                    verdict = grade(game.final, instance, validate_metrics)
                    self.assertTrue(verdict["result_valid"])
                    self.assertEqual(verdict["primary_score"], 0)
                    self.assertTrue(math.isclose(verdict["return"], 0))
                finally:
                    game.close()


    def extended_instance(self, family):
        task = GAME_ROOT / "tasks/vizdoom" / f"vizdoom-{family}-i01-standard"
        instance = validate_instance(json.loads((task / "tests/instance.json").read_text()))
        actions = json.loads((task / "solution/actions.json").read_text())
        return instance, actions

    def test_all_new_reference_sessions_match_native_actions_and_grade(self):
        for family in instance_schema.SCENARIOS:
            if family in {"basic", "my-way-home"}:
                continue
            with self.subTest(family=family), tempfile.TemporaryDirectory() as directory:
                instance, actions = self.extended_instance(family)
                spec = instance_schema.SCENARIOS[family]
                game = ViZDoomSession.open(Adapter, instance, Path(directory), Path(directory) / "record")
                self.addCleanup(game.close)
                self.assertIsNone(game.final)
                native = self.native(instance, spec, directory)
                for i, (action, tics, *axes) in enumerate(actions):
                    if native.is_episode_finished():
                        break
                    buttons = action.split("+")
                    deltas = axes[0] if axes else {}
                    vector = [deltas.get(button, int(button in buttons)) for button in instance["buttons"]]
                    native.make_action(vector, tics)
                    wire = encode_action(action, tics, deltas if axes else None)
                    obs = game.submit({"action": wire, "expected_step": i, "request_id": str(i)})
                    self.assertAlmostEqual(game.adapter.native_return, native.get_total_reward(), places=9)
                    self.assertEqual(obs["done"], native.is_episode_finished())
                    if not obs["done"]:
                        self.assertTrue(np.array_equal(game.adapter.frame(), native.get_state().screen_buffer))
                game.finalize("agent_finished")
                verdict = grade(game.final, instance, validate_metrics)
                self.assertTrue(verdict["result_valid"])
                if spec["goal"]:
                    self.assertTrue(game.final["success"])
                    self.assertEqual(verdict["primary_score"], 1)
                else:
                    self.assertEqual(verdict["primary_metric"], "native_return")
                    self.assertEqual(verdict["primary_score"], game.adapter.native_return)
                game.close()
                native.close()

    def test_notification_and_native_no_goal_timeout_behavior(self):
        instance, _ = self.extended_instance("basic-notifications")
        with tempfile.TemporaryDirectory() as directory:
            game = ViZDoomSession.open(Adapter, instance, None, Path(directory))
            self.addCleanup(game.close)
            first = game.observe()
            self.assertEqual(set(first["observation"]), {"frame_available", "image_png_base64", "notifications"})
            action = game.submit({"action":"noop@100", "expected_step":0, "request_id":"read-notice"})
            self.assertTrue(action["observation"]["notifications"].strip().startswith("Shoot:"))
            final = game.submit({"action":"noop@999", "expected_step":1, "request_id":"wait"})
            self.assertTrue(final["done"])
            self.assertFalse(game.final["success"])
            self.assertEqual(game.final["reason"], "native_truncated")
            self.assertTrue(grade(game.final, instance, validate_metrics)["result_valid"])

    def test_basic_notifications_wrong_kill_is_valid_failure(self):
        instance, _ = self.extended_instance("basic-notifications")
        with tempfile.TemporaryDirectory() as directory:
            game = ViZDoomSession.open(Adapter, instance, None, Path(directory))
            try:
                for i, action in enumerate(("MOVE_LEFT@13", "ATTACK@300")):
                    game.submit({"action": action, "expected_step": i, "request_id": str(i)})
                self.assertEqual(game.adapter.game.get_game_variable(vzd.GameVariable.KILLCOUNT), 1)
                self.assertEqual(game.final["metrics"]["objective_success"], 0)
                self.assertTrue(grade(game.final, instance, validate_metrics)["result_valid"])
            finally:
                game.close()

    def test_wall_clock_can_interrupt_long_action_without_native_limit(self):
        for family in ("take-cover", "defend-line"):
            instance, _ = self.extended_instance(family)
            with self.subTest(family=family), tempfile.TemporaryDirectory() as directory:
                game = ViZDoomSession.open(Adapter, instance, None, Path(directory))
                self.addCleanup(game.close)
                def tick():
                    if game.adapter.advanced_tics == 3:
                        game.started -= game.wall_clock
                    return game.action_deadline_reached()
                game.adapter.action_deadline_reached = tick
                obs = game.submit({"action":"noop@999999999", "expected_step":0, "request_id":"deadline"})
                self.assertTrue(obs["done"])
                self.assertEqual(game.final["reason"], "time_limit")
                self.assertEqual(game.final["metrics"]["action_tics"], [[999999999,3]])
                self.assertTrue(grade(game.final, instance, validate_metrics)["result_valid"])

    def test_deathmatch_spec_supports_valid_axis_values_and_rejects_bad_actions(self):
        instance, _ = self.extended_instance("deathmatch")
        with tempfile.TemporaryDirectory() as directory:
            game = ViZDoomSession.open(Adapter, instance, None, Path(directory))
            self.addCleanup(game.close)
            spec = game.spec()
            self.assertEqual(len(spec["binary_buttons"]), 17)
            self.assertEqual(len(spec["delta_buttons"]), 3)
            for wire in ("ATTACK+ATTACK@2", "ATTACK~nan,0,0@1", "noop~0,0@1", "noop@0"):
                with self.assertRaises(InvalidAction):
                    game.submit({"action":wire, "expected_step":0, "request_id":wire})
            self.assertEqual(game.adapter.advanced_tics,0)
            with self.assertRaises(ValueError):
                encode_action("noop", 1, {"TURN_LEFT_RIGHT_DELTA": float("inf")})
            wire = encode_action("+".join(spec["binary_buttons"]),1,{b: -0.25 for b in spec["delta_buttons"]})
            game.submit({"action":wire,"expected_step":0,"request_id":"continuous"})
            self.assertEqual(game.adapter.advanced_tics,1)
            game.close()


if __name__ == "__main__":
    unittest.main()
