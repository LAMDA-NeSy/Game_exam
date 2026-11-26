"""FLE adapter boundaries and a known trajectory scored by the pinned authors' code."""
import json
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import Mock

TASK = Path(__file__).resolve().parents[1] / "benchmarks/factorio/iron_plate_throughput"
sys.path[:0] = [str(TASK / "environment"), str(TASK / "tests")]
from adapter import Episode, Handler
from grade import grade, validate


class FactorioTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.output = self.root / "episode.json"
        self.reply = {"reward": 2, "production_score": 8, "automated_production_score": 4,
                      "terminated": False, "truncated": False, "error_occurred": False,
                      "game_state_raw": "private upstream snapshot", "result": "observed"}
        self.bridge = Mock(side_effect=lambda cmd, payload=None:
                           {"reset": {}, "observe": {"entities": []}, "system-prompt": {"system_prompt": "api"},
                            "execute": self.reply}[cmd])
        self.session = Episode(self.bridge, self.output)

    def test_retry_is_one_native_action(self):
        result = self.session.execute(1, "print(1)")
        self.assertEqual(result, self.session.execute(1, "print(1)"))
        self.assertNotIn("game_state_raw", result)
        with self.assertRaises(ValueError):
            self.session.execute(1, "print(2)")
        self.assertEqual([call.args for call in self.bridge.call_args_list if call.args[0] == "execute"],
                         [("execute", {"agent_idx": 0, "code": "print(1)"})])
        for route in ("/reset", "/game-state", "/execute"):
            with self.assertRaises(ValueError):
                self.session.dispatch("POST", route, {})

    def test_native_end_and_budget(self):
        for i in range(1, 65):
            self.session.execute(i, "print(1)")
        with self.assertRaises(ValueError):
            self.session.execute(65, "print(1)")
        self.assertFalse(self.session.steps[-1]["terminated"])

    def test_native_termination_ends_episode_before_budget(self):
        self.reply.update(terminated=True, reward=16)
        self.assertIsNone(self.session.execute(1, "sleep(60)")["next_step"])
        with self.assertRaises(ValueError):
            self.session.execute(2, "sleep(60)")

    def test_failed_native_step_cannot_be_retried_or_graded(self):
        self.bridge.side_effect = RuntimeError("native connection lost")
        with HTTPServer(("127.0.0.1", 0), Handler) as server:
            server.episode = self.session
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for command, payload in (("step", {"number": 1, "code": "sleep(1)"}),
                                         ("step", {"number": 1, "code": "sleep(1)"}), ("seal", {})):
                    conn = HTTPConnection(*server.server_address, timeout=5)
                    try:
                        conn.request("POST", "/" + command, json.dumps(payload))
                        response = conn.getresponse()
                        self.assertEqual(response.status, 503)
                        self.assertIn("native connection lost", json.load(response)["error"])
                    finally:
                        conn.close()
            finally:
                server.shutdown()
                thread.join()
        self.assertEqual(sum(call.args[0] == "execute" for call in self.bridge.call_args_list), 1)
        saved = json.loads(self.output.read_text())
        self.assertIsNotNone(saved["fault"])
        self.assertFalse(saved["sealed"])

    def test_native_scorer_and_target_are_distinct(self):
        from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import iron_plate_throughput

        self.session.execute(1, "print(1)")
        with self.assertRaises(ValueError):
            validate(json.loads(self.output.read_text()), iron_plate_throughput)
        self.session.dispatch("POST", "/seal", {})
        with self.assertRaises(ValueError):
            self.session.execute(2, "print(2)")
        episode = json.loads(self.output.read_text())
        grade(episode, self.root)
        self.assertEqual(json.loads((self.root / "reward.json").read_text()),
                         {"fle_inspect_score": 0.5, "iron_plate_goal_reached": 0})
        episode["fault"] = "bridge disconnected"
        with self.assertRaises(ValueError):
            validate(episode, iron_plate_throughput)


if __name__ == "__main__":
    unittest.main()
