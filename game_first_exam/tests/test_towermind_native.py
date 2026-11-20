"""Native equivalence and timing checks for the pinned TowerMind Linux player."""
import socket
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest

import numpy as np

from towermind_fixture import instance
from adapter import Adapter, NATIVE_ASSETS
from native import RPC_PORT, open_native
from native_assets import prepare_game
from metric_rules import validate_metrics
from server import Game


COMMANDS = [("0 0 0", (0.0, 0.0, 0)), ("-1.5 1.2 2", (-1.5, 1.2, 2))] * 6


def native_snapshot(observation, reward, done, interrupted):
    return observation["text"], float(reward), bool(done), bool(interrupted)


class TowerMindNative(unittest.TestCase):
    def test_native_trajectory_and_idle_intervals(self):
        config = instance()
        with TemporaryDirectory() as workspace:
            player, _ = prepare_game(NATIVE_ASSETS, Path(workspace), config)
            env, initial = open_native(player, NATIVE_ASSETS / "wrappers.py", config["seed"])
            try:
                with self.assertRaisesRegex(RuntimeError, "one episode"):
                    env.reset()
                with socket.create_connection(("127.0.0.1", RPC_PORT), timeout=2):
                    pass
                expected = []
                for _, action in COMMANDS:
                    observation, reward, done, info = env.step(action)
                    interrupted = info["step"].interrupted[0] if done else False
                    expected.append(native_snapshot(observation, reward, done, interrupted))
                    self.assertFalse(done)
            finally:
                env.close()

        adapter = Adapter(config)
        try:
            self.assertEqual(adapter._state, initial["text"])
            initial_frame = initial["image"]
            if initial_frame.shape == (3, 512, 512):
                initial_frame = initial_frame.transpose(1, 2, 0)
            self.assertEqual(adapter.frame().shape, initial_frame.shape)
            self.assertEqual(adapter.frame().dtype, np.uint8)
            for index, ((command, _), item) in enumerate(zip(COMMANDS, expected)):
                before = adapter.fingerprint()
                adapter.spec()
                adapter.observe()
                adapter.frame()
                if index in (1, 5):
                    time.sleep(1)
                    adapter.observe()
                self.assertEqual(adapter.fingerprint(), before)
                transition = adapter.step(command)
                self.assertEqual(
                    (adapter._state, transition.reward, transition.terminated or transition.truncated,
                     transition.truncated),
                    item,
                )
        finally:
            adapter.close()

    def test_native_terminal_uses_first_episode(self):
        config = instance()
        adapter = Adapter(config)
        try:
            for _ in range(4096):
                transition = adapter.step("0 0 0")
                if transition.terminated or transition.truncated:
                    break
            self.assertTrue(transition.terminated, "expected a native ending in development level 0")
            metrics = adapter.metrics()
            self.assertEqual(metrics["native_return"], metrics["base_health"] - metrics["initial_base_health"])
            self.assertEqual(adapter.success(), metrics["base_health"] > 0)
            with self.assertRaisesRegex(ValueError, "episode closed"):
                adapter.step("0 0 0")
        finally:
            adapter.close()

    def test_public_service_stops_without_awarding_completion(self):
        config = instance()
        config["max_steps"] = 1
        adapter = Adapter(config)
        config["initial_state_sha256"] = adapter.fingerprint()
        with TemporaryDirectory() as directory:
            game = Game(adapter, config, directory)
            try:
                reply = game.submit({"action": "0 0 0", "expected_step": 0, "request_id": "native-first"})
                self.assertTrue(reply["done"])
                self.assertEqual(set(reply["observation"]), {"image_png_base64"})
                self.assertEqual(game.final["reason"], "step_limit")
                self.assertFalse(game.final["success"])
                validate_metrics(game.final, config)
                self.assertIsNone(game.recorder.error)
            finally:
                game.close()


if __name__ == "__main__":
    unittest.main()
