"""Regression cases for the native Forest Temple exit objective."""
import importlib.util
import unittest
from pathlib import Path

source = Path(__file__).resolve().parents[1] / "benchmarks/firewater/metric_rules.py"
spec = importlib.util.spec_from_file_location("firewater_metrics", source)
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)


def verdict(outcome=None, reason=None, *, red=0, blue=0):
    won = outcome == "success"
    return {"terminated": outcome is not None, "success": won, "return": float(won),
            "metrics": {"level": 1, "fireboy": red, "watergirl": blue,
                        "terminal_outcome": outcome, "terminal_reason": reason,
                        "success": int(won)}}


class ForestExitTests(unittest.TestCase):
    def test_native_completion(self):
        for red, blue in ((3, 4), (0, 0)):
            rules.validate_metrics(verdict("success", "level_completed", red=red, blue=blue), {})

    def test_diamonds_without_exit_do_not_win(self):
        for outcome, reason in ((None, None), ("fail", "level_failed"), ("fail", "level_ended")):
            final = verdict(outcome, reason, red=3, blue=4)
            rules.validate_metrics(final, {})
            final.update(success=True, **{"return": 1.0})
            with self.assertRaises(ValueError):
                rules.validate_metrics(final, {})

    def test_disagrees_with_native_event(self):
        for key, value in (("level", 2), ("terminal_reason", None), ("watergirl", -1)):
            final = verdict("success", "level_completed")
            final["metrics"][key] = value
            with self.assertRaises(ValueError):
                rules.validate_metrics(final, {})
