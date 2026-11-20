#!/usr/bin/env python3
"""Check the five frozen V-MAGE smoke oracle results and their evidence."""
import argparse
import json
from pathlib import Path


# Game, then expected (raw score, accepted decisions). Race reaches a goal;
# the other four traces deliberately end after demonstrating positive scoring.
EXPECTED = {
    "vmage-race-l01-i01-standard": (100, 4),
    "vmage-flappybird-l01-i01-standard": (1, 40),
    "vmage-pong-l01-i01-standard": (1, 29),
    "vmage-supermario-l01-i01-standard": (100, 11),
    "vmage-tempestrun-l01-i01-standard": (10, 2),
}
RACE = "vmage-race-l01-i01-standard"


def read(path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check(job):
    paths = sorted(job.glob("*/result.json"))
    require(len(paths) == len(EXPECTED), "expected exactly five completed trials")
    require(read(job / "game-provenance.json")["status"] == "complete", "provenance incomplete")
    require(read(job / "runtime-images.json")["complete"] is True, "runtime image capture incomplete")
    summary = read(job / "game-report/summary.json")
    require(summary["complete"] and summary["expected_trials"] == summary["valid_trials"] == len(EXPECTED),
            "derived report incomplete")

    evidence = {}
    for path in paths:
        result = read(path)
        task = result["task_name"].rsplit("/", 1)[-1]
        require(task in EXPECTED and task not in evidence, f"unexpected or duplicate task: {task}")
        score, steps = EXPECTED[task]
        require(result.get("exception_info") is None, f"{task}: Harbor trial raised an exception")
        agent = result.get("agent_info", {})
        require(agent.get("name") == "oracle" and agent.get("model_info") is None,
                f"{task}: smoke must run without a model")

        trial = path.parent
        reward = read(trial / "verifier/reward.json")
        require(reward.get("result_valid") == 1, f"{task}: invalid result")
        for key in ("infra_error", "sim_error", "environment_error"):
            require(reward.get(key) == 0, f"{task}: {key} is not zero")
        require(reward.get("primary_score") == score and reward.get("steps") == steps,
                f"{task}: expected {score} raw points in {steps} actions")

        data = trial / "artifacts/data"
        final = read(data / "final.json")
        require(final["finalized"] and final["result_valid"], f"{task}: invalid simulator evidence")
        require(final["metrics"]["native_score"] == score and final["steps"] == steps,
                f"{task}: simulator and verifier disagree")
        require(not final["truncated"], f"{task}: unexpected truncation")
        if task == RACE:
            require(final["terminated"] and final["reason"] == "native_terminated"
                    and final["metrics"]["native_win"] and final["metrics"]["terminal_cause"] == "native_win"
                    and final["success"] and reward.get("success") == 1,
                    f"{task}: oracle did not reach the trophy")
        else:
            require(not final["terminated"] and final["reason"] == "agent_finished"
                    and final["metrics"]["terminal_cause"] == "running",
                    f"{task}: partial reference ended unexpectedly")

        recording = read(data / "recording.json")
        require(recording.get("video_source") == "live" and recording.get("render_error") is None,
                f"{task}: live recording failed")
        for name in ("episode.jsonl", "replay.mp4"):
            artifact = data / name
            require(artifact.is_file() and artifact.stat().st_size > 0, f"{task}: {name} missing")
        # A short run can finish before resource sampling. Preserve those flags.
        evidence[task] = dict(score=score, steps=steps, end=final["reason"],
                              resource_monitor_missing=reward.get("resource_monitor_missing"),
                              resource_enforced=reward.get("resource_enforced"))
    print(json.dumps(evidence, indent=2, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    check(parser.parse_args().job)
