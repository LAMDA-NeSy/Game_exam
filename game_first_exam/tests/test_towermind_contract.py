"""Verify the public projection, action validation and grading without launching Unity."""
import base64
from contextlib import contextmanager
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from towermind_fixture import instance
import adapter
from config_schema import validate_instance
from grade import grade
from metric_rules import validate_metrics
from native_assets import ARCHIVE_SHA256
from server import Game, InvalidAction


def native_observation(health, shade=91):
    return {
        "image": np.full((512, 512, 3), shade, dtype=np.uint8),
        "text": {"Level_Current_Health": health, "private": "hidden-wave-sentinel"},
    }


class StubNative:
    def __init__(self, outcome):
        self.outcome = outcome
        self.actions = []
        self.closed = False

    def step(self, action):
        self.actions.append(action)
        health = 0 if self.outcome == "destroyed" else 20
        return native_observation(health, 92), health - 20, True, {
            "step": SimpleNamespace(interrupted=[self.outcome == "interrupted"])
        }

    def close(self):
        self.closed = True


@contextmanager
def session(outcome):
    config = instance()
    native = StubNative(outcome)
    with TemporaryDirectory() as output:
        with (
            patch.object(adapter, "version", side_effect=config["engine_versions"].__getitem__),
            patch.object(adapter, "prepare_game", return_value=(Path("unused"), 20)),
            patch.object(adapter, "open_native", return_value=(native, native_observation(20))),
        ):
            game_adapter = adapter.Adapter(config)
        config["initial_state_sha256"] = game_adapter.fingerprint()
        with patch("server.Recorder.frame"):  # PNG projection is covered below; no encoder needed here.
            game = Game(game_adapter, config, output)
            try:
                yield game, config, native
            finally:
                game.close()


class TowerMindContract(unittest.TestCase):
    def test_gym_bridge_can_load_offline(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("unexpected runtime download")):
            from native import load_gym_bridge

            self.assertEqual(load_gym_bridge().__name__, "UnityToGymWrapper")

    def test_initial_decision_comes_from_explicit_reset_after_handshake(self):
        import native

        unity = native.LocalUnity.__new__(native.LocalUnity)
        payloads = iter(("", '{"Level_Current_Health": 20}'))
        unity.get_steps = lambda _: ([object()], [])

        def receive_reset(player):
            player.payload = next(payloads)

        class GymBridge:
            name = "tower-defender"

            def __init__(self, player, **_):
                self.player = player
                player.reset()  # Slot discovery sees an empty text sensor.

            def reset(self):
                self.player.reset()
                return {"text": json.loads(self.player.payload)}

        wrappers = SimpleNamespace(
            TowerMindMultiModalObsWrapper=lambda gym, **_: gym,
            TowerMindActionMappingWrapper=lambda env: env,
        )
        with (
            patch.object(native, "LocalUnity", return_value=unity),
            patch.object(native, "load_gym_bridge", return_value=GymBridge),
            patch.object(native, "load_source", return_value=wrappers),
            patch.object(native.UnityEnvironment, "reset", autospec=True, side_effect=receive_reset) as reset,
        ):
            env, initial = native.open_native(Path("td.x86_64"), Path("wrappers.py"), 42)
            self.assertEqual(initial["text"]["Level_Current_Health"], 20)
            with self.assertRaisesRegex(RuntimeError, "one episode"):
                env.reset()
            self.assertEqual(reset.call_count, 2)

    def test_schema_rejects_drift(self):
        config = instance()
        self.assertEqual(config["engine_archive_sha256"], ARCHIVE_SHA256)
        validate_instance(config)
        for update in ({"seed": 0}, {"level_id": 9}, {"engine_archive_sha256": "1" * 64},
                       {"observation_profile": "unfiltered-json"}, {"hidden_field": True}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                validate_instance(dict(config, **update))

    def test_rgb_is_only_public_observation_and_reading_is_pure(self):
        with session("completed") as (game, config, native):
            before = game.adapter.fingerprint()
            self.assertEqual(game.spec()["reset_budget"], 0)
            observation = game.observe()["observation"]
            self.assertEqual(set(observation), {"image_png_base64"})
            with Image.open(BytesIO(base64.b64decode(observation["image_png_base64"]))) as image:
                self.assertEqual((image.mode, image.size, image.getpixel((0, 0))), ("RGB", (512, 512), (91, 91, 91)))
            self.assertEqual(game.observe()["observation"], observation)
            self.assertEqual(game.adapter.fingerprint(), before)
            self.assertEqual(native.actions, [])
            self.assertNotIn("hidden-wave-sentinel", str(game.spec()))
            self.assertNotIn(config["engine_archive_sha256"], str(game.spec()))
        self.assertTrue(native.closed)

    def test_server_rejects_malformed_action_before_game_moves(self):
        with session("completed") as (game, _, native):
            for action in ("reset", "3.01 0 1", "0 0 12", "nan 0 0", "0 0 0\n", "0  0 1", [0, 0, 0]):
                with self.subTest(action=action), self.assertRaises(InvalidAction):
                    game.submit({"action": action, "expected_step": 0, "request_id": "bad"})
            self.assertEqual((game.steps, native.actions), (0, []))

    def test_native_outcomes_and_public_early_stop_are_distinct(self):
        for outcome, reason, success in (
            ("completed", "native_terminated", 1),
            ("destroyed", "native_terminated", 0),
            ("interrupted", "native_truncated", 0),
            ("early", "agent_finished", 0),
        ):
            with self.subTest(outcome=outcome), session(outcome) as (game, config, native):
                if outcome == "early":
                    game.finalize("agent_finished")
                else:
                    action = {"action": "-3.000000000 3.000000000 11", "expected_step": 0, "request_id": "legal"}
                    self.assertTrue(game.submit(action)["done"])
                    self.assertTrue(game.submit(action)["done"])  # duplicate must not execute again
                    self.assertEqual(native.actions, [(-3.0, 3.0, 11)])
                result = grade(game.final, config, validate_metrics)
                self.assertEqual((result["reason"], result["primary_score"]), (reason, success))


if __name__ == "__main__":
    unittest.main()
