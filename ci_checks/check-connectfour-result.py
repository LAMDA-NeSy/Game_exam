#!/usr/bin/env python3
"""Check the winning and losing Harbor trials independently."""

import json
import sys
from pathlib import Path


def check(job: Path, outcome: str, score: int):
    trials = list(job.glob("*/result.json"))
    if len(trials) != 1:
        raise ValueError(f"{job}: expected one completed trial, found {len(trials)}")

    trial = trials[0].parent
    result = json.loads(trials[0].read_text())
    reward = json.loads((trial / "verifier/reward.json").read_text())
    final = json.loads((trial / "artifacts/data/final.json").read_text())
    recording = json.loads((trial / "artifacts/data/recording.json").read_text())

    if result.get("exception_info") is not None or result["task_name"].split("/")[-1] != "connectfour-match-i01-standard":
        raise ValueError(f"{job}: wrong task or Harbor exception")
    if reward["result_valid"] != 1 or reward["primary_score"] != score or reward["success"] != score:
        raise ValueError(f"{job}: unexpected verifier grade")
    if any(reward.get(key) != 0 for key in ("infra_error", "sim_error", "environment_error")):
        raise ValueError(f"{job}: environment or simulator error")
    if (final["metrics"]["outcome"] != outcome or final["success"] != bool(score)
            or final["metrics"]["agent_decisions"] != 12 or final["steps"] != 12):
        raise ValueError(f"{job}: native match did not reach its expected outcome")
    if recording.get("render_error") is not None or not (trial / "artifacts/data/replay.mp4").stat().st_size:
        raise ValueError(f"{job}: replay missing or rendering failed")
    print(f"{job}: {outcome}, score {score}, 12 decisions, replay recorded")


if __name__ == "__main__":
    check(Path(sys.argv[1]), "win", 1)
    check(Path(sys.argv[2]), "loss", 0)
