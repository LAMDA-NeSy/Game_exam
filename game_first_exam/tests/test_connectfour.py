"""Native matches, deterministic opponent, and independent replay verification."""

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / folder) for folder in (
    "scripts", "game_first_exam/runtime", "game_first_exam/benchmarks/connectfour"
)]

from adapter import Adapter
from game_schemas import load_schema
from grade import grade
from metric_rules import validate_metrics
from server import Game


TASK = ROOT / "game_first_exam/tasks/connectfour/connectfour-match-i01-standard"
INSTANCE = json.loads((TASK / "tests/instance.json").read_text())
WIN = json.loads((TASK / "solution/route.json").read_text())
LOSS = json.loads((ROOT / "game_first_exam/tests/benchmarks/connectfour/loss/route.json").read_text())


class ConnectFourTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_schema("connectfour")

    def play(self, route, expected):
        with tempfile.TemporaryDirectory() as output, patch.dict(os.environ, {
            "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"
        }):
            game = Game.open(Adapter, INSTANCE, None, output)
            try:
                self.assertIsNone(game.final)
                opening = game.adapter.fingerprint()
                self.assertEqual(opening, INSTANCE["initial_state_sha256"])
                observation = game.observe()
                self.assertEqual(observation["observation"]["legal_columns"], list(range(7)))
                self.assertEqual(game.adapter.fingerprint(), opening)
                for column in route:
                    if game.final is not None:
                        break
                    observation = game.submit({"action": str(column), "expected_step": game.steps,
                                               "request_id": str(game.steps)})
                self.assertEqual(game.final["metrics"]["outcome"], expected)
                self.assertEqual(game.final["metrics"]["agent_decisions"], len(route))
                reward = grade(game.final, INSTANCE, validate_metrics)
                self.assertEqual(reward["primary_score"], int(expected == "win"))
                self.assertEqual(reward["environment_error"], 0)
                self.assertTrue((Path(output) / "replay.mp4").stat().st_size > 0)
                return game.final
            finally:
                game.close()

    def test_reference_wins_and_control_loses_on_identical_opening(self):
        self.play(WIN, "win")
        self.play(LOSS, "loss")

    def test_verifier_rejects_tampered_native_moves(self):
        final = self.play(WIN, "win")
        fake = copy.deepcopy(final)
        fake["metrics"]["moves"][1]["column"] = 6
        with self.assertRaisesRegex(ValueError, "opponent"):
            grade(fake, INSTANCE, validate_metrics)
        fake = copy.deepcopy(final)
        fake["metrics"]["outcome"] = "loss"
        with self.assertRaisesRegex(ValueError, "final metrics"):
            grade(fake, INSTANCE, validate_metrics)


if __name__ == "__main__":
    unittest.main()
