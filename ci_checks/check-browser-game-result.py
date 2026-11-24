"""Verify the Harbor verdict from a browser game's reference or control run."""
import json
import sys
from pathlib import Path


def check(trial_dir, expected):
    paths = (
        trial_dir.glob("*/verifier/reward.json") if expected == 1 else
        (path for path in trial_dir.glob("*/*/verifier/reward.json")
         if path.parents[2].name != "browser-reference")
    )
    rewards = list(paths)
    if len(rewards) != 1:
        raise ValueError(f"Expected one verifier result under {trial_dir}, found {len(rewards)}")
    reward = json.loads(rewards[0].read_text())
    errors = ("infra_error", "sim_error", "environment_error")
    if (not reward.get("result_valid") or any(reward.get(key) != 0 for key in errors)
            or reward.get("steps", 0) <= 0 or reward.get("success") != expected):
        raise ValueError(f"Expected a valid result with success={expected}: {reward}")
    print(f"{rewards[0]}: success={expected}, steps={reward['steps']}")


if __name__ == "__main__":
    check(Path(sys.argv[1]), int(sys.argv[2]))
