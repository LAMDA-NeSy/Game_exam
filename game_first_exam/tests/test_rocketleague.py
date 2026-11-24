import unittest
from pathlib import Path
from runpy import run_path

rules = Path(__file__).resolve().parents[1] / "benchmarks/rocketleague/metric_rules.py"
validate = run_path(str(rules))["validate_metrics"]


class FirstGoalTests(unittest.TestCase):
    def check_score(self, own, opponent, ended, won):
        validate({"metrics": {"goals_for": own, "goals_against": opponent, "success": int(won)},
                  "terminated": ended, "success": won, "return": float(won)}, {})

    def test_scorelines(self):
        self.check_score(1, 0, True, True)
        self.check_score(0, 1, True, False)
        self.check_score(0, 0, False, False)

    def test_inconsistent_records(self):
        for record in [(1, 1, True, True), (0, 1, True, True), (0, 0, True, False)]:
            with self.subTest(record=record), self.assertRaises(ValueError):
                self.check_score(*record)
