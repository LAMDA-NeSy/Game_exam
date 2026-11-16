#!/usr/bin/env python3
"""Fail CI if Harbor returned but the README Room oracle did not produce valid evidence."""
import json
import sys
from pathlib import Path


def check(job: Path):
    def read(path):
        return json.loads(path.read_text())

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    trials = sorted(job.glob("*/result.json"))
    require(len(trials) == 1, "expected exactly one completed trial")
    result = read(trials[0])
    require(result.get("exception_info") is None, "Harbor trial raised an exception")
    require(result.get("agent_info", {}).get("name") == "oracle", "smoke must not call a model")
    require(result["task_name"].rsplit("/", 1)[-1] == "minihack-room-i01-standard", "unexpected task")
    trial = trials[0].parent
    rewards = read(trial / "verifier/reward.json")
    require(rewards.get("result_valid") == 1, "invalid result")
    require(rewards.get("success") == 1 and rewards.get("primary_score") == 100, "Room oracle failed")
    for field in ("infra_error", "sim_error", "environment_error"):
        require(rewards.get(field) == 0, f"{field} is not zero")
    final = read(trial / "artifacts/data/final.json")
    require(final["success"] and final["steps"] == rewards["steps"] == 4, "native oracle trajectory changed")
    require(read(trial / "artifacts/data/recording.json").get("render_error") is None, "render failed")
    video = trial / "artifacts/data/replay.mp4"
    require(video.is_file() and video.stat().st_size > 0, "replay missing")
    require(read(job / "game-provenance.json")["status"] == "complete", "provenance incomplete")
    require(read(job / "runtime-images.json")["complete"] is True, "runtime image capture incomplete")
    require(read(job / "game-report/summary.json")["complete"] is True, "derived report incomplete")
    # Four native actions may finish before monitor sampling. Report this explicitly;
    # it is not evidence of resource enforcement, and is not a game failure.
    print(json.dumps({"task": result["task_name"], "score": rewards["primary_score"],
                      "steps": rewards["steps"], "resource_monitor_missing": rewards.get("resource_monitor_missing"),
                      "resource_enforced": rewards.get("resource_enforced"), "evidence": "complete"}, indent=2))


if __name__ == "__main__":
    check(Path(sys.argv[1]))
