#!/usr/bin/env python3
"""Validate a Pac-Man Harbor reference or failure job from trusted artifacts."""

import json
import sys
from pathlib import Path


def check(job: Path, expected_success: int):
    trials = sorted(job.glob("*/result.json"))
    if len(trials) != 1:
        raise ValueError(f"Expected one Pac-Man trial in {job}, got {len(trials)}")

    result = json.loads(trials[0].read_text())
    if result.get("exception_info") is not None:
        raise ValueError(f"Harbor raised an exception: {result['exception_info']}")
    if result.get("agent_info", {}).get("name") != "oracle":
        raise ValueError("Reference run must use the oracle agent")
    if result["task_name"].rsplit("/", 1)[-1] != "pacman-600-i01-standard":
        raise ValueError("Wrong Pac-Man task")

    trial = trials[0].parent
    reward = json.loads((trial / "verifier/reward.json").read_text())
    final = json.loads((trial / "artifacts/data/final.json").read_text())
    for key in ("infra_error", "sim_error", "environment_error"):
        if reward.get(key) != 0:
            raise ValueError(f"{key}: {reward.get(key)}")
    if (reward.get("result_valid") != 1 or reward.get("success") != expected_success
            or reward.get("primary_score") != expected_success or reward.get("steps", 0) <= 0):
        raise ValueError(f"Unexpected verifier outcome: {reward}")

    metrics = final["metrics"]
    if final.get("initial_state_sha256") != "628cb4ead38e34e34a34f78fa4481f2a0ccf8e9139acfae69d79dc997e90e36b":
        raise ValueError("Pac-Man opening changed")
    if final.get("steps") != reward["steps"] or final.get("success") != bool(expected_success):
        raise ValueError("Native result disagrees with verifier")
    if expected_success:
        if metrics["score"] < 600 or metrics["deaths"] != 0:
            raise ValueError(f"Reference did not clear 600 points: {metrics}")
    elif metrics["score"] >= 600 or metrics["deaths"] < 1:
        raise ValueError(f"Control did not end in game over below 600: {metrics}")
    print(f"{job}: valid Pac-Man {'clear' if expected_success else 'failure'}, "
          f"score={metrics['score']}, steps={reward['steps']}")


if __name__ == "__main__":
    check(Path(sys.argv[1]), int(sys.argv[2]))
