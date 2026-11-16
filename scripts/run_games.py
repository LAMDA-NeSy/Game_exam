#!/usr/bin/env python3
"""Compatibility CLI. Prefer native `harbor run --game-suite ... --standard -a ... -m ...` (or -c).

Harbor owns execution and config/lock/result records. GameRecords only adds
runtime provenance and game-specific derived scores; no suite snapshot is written.
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

# Preserve callers importing the old aggregation functions.
from game_reports import aggregate, summarize_trial, write_harbor_report, write_report
from prepare_games import ROOT, load_suite, prepare, select_tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--suite", default="core")
    parser.add_argument("--benchmark", action="append", default=[])
    parser.add_argument("--family", action="append", default=[])
    parser.add_argument(
        "--agent", default="oracle", help="Harbor native agent name or import path; tamper is a test fixture"
    )
    parser.add_argument("--mode", choices=("standard", "privileged", "realtime"))
    parser.add_argument("--ak", action="append", default=[], help="Native Harbor agent key=value option (repeatable)")
    parser.add_argument("--model")
    parser.add_argument("--agent-version", help="override the agent CLI version in the native config")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--name")
    parser.add_argument("--jobs-dir", type=Path, default=ROOT / "jobs")
    parser.add_argument("--report-only", type=Path)
    args = parser.parse_args()
    if args.report_only:
        job = args.report_only.resolve()
        if (job / "game-provenance.json").exists():
            summary = write_harbor_report(job)
        else:
            # Old evidence is not migrated or rewritten with a different scorer.
            summary = write_report(job, json.loads((job / "suite-snapshot.json").read_text()))
        print(json.dumps(summary["benchmarks"], indent=2))
        return 0 if summary["complete"] else 1
    if args.concurrency < 1:
        parser.error("positive concurrency is required")
    if args.agent in {"oracle", "nop", "tamper"} and (args.model or args.agent_version or args.ak):
        parser.error("reference/no-op agents do not take model settings")
    suite, plans = load_suite(args.suite)
    selected = select_tasks(suite, args.benchmark, args.family)
    if args.mode:
        selected = [row for row in selected if row["name"].endswith("-" + args.mode)]
        if not selected:
            parser.error(f"this suite has no {args.mode} tasks")
    if args.validate_only:
        print(f"Validated {len(plans)} tasks; no images built and no evaluation launched")
        return 0
    jobs = args.jobs_dir.resolve()
    name = args.name or f"games-{args.agent}-{uuid.uuid4().hex[:12]}"
    if Path(name).name != name or name in (".", "..") or (jobs / name).exists():
        parser.error("choose a new single-directory job name")
    # Retain the old Codex preset only for legacy callers. Other agents are passed to
    # Harbor without a fork-specific support list or copied agent implementations.
    profile = {"codex": "codex-deepseek", "tamper": "oracle", "oracle": "oracle", "nop": "nop"}.get(args.agent)
    config = ROOT / "configs/harbor" / f"{profile}.json" if profile else None
    if args.model or args.agent_version or config is None:
        data = json.loads(config.read_text()) if config else {"agents": [{"name": args.agent, "kwargs": {}}]}
        agent = data["agents"][0]
        if args.model:
            agent["model_name"] = args.model
        if args.agent_version:
            agent.setdefault("kwargs", {})["version"] = args.agent_version
        config = jobs / "prepared" / f"{name}.agent.json"
        config.parent.mkdir(parents=True, exist_ok=True)
        with config.open("x") as stream:
            stream.write(json.dumps(data, indent=2) + "\n")
    selection = ["--game-suite", args.suite]
    if args.mode:
        selection += ["--" + args.mode]
    for benchmark in args.benchmark:
        selection += ["--benchmark", benchmark]
    for family in args.family:
        selection += ["--family", family]
    if args.agent == "tamper":
        staged = prepare(suite, plans, selected, jobs / "prepared" / f"{name}.json", tamper=True)
        selection = ["-c", str(staged)]
    cmd = [
        str(Path(sys.executable).with_name("harbor")),
        "run",
        *selection,
        "-c",
        str(config),
        "--jobs-dir",
        str(jobs),
        "--job-name",
        name,
        "--n-concurrent",
        str(args.concurrency),
        "--plugin",
        "game_harbor:GameRecords",
        "-y",
    ]
    for kwarg in args.ak:
        cmd += ["--ak", kwarg]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "scripts") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    print(
        "Compatibility entry: delegating to native Harbor; primary records are config.json, lock.json and result.json.",
        flush=True,
    )
    code = subprocess.run(cmd, cwd=ROOT, env=env, check=False).returncode
    report = jobs / name / "game-report/summary.json"
    if code:
        return code
    if not report.exists():
        print("Game report missing; inspect Harbor job.log and game-provenance.json", file=sys.stderr)
        return 1
    summary = json.loads(report.read_text())
    print("Game report:", report.parent / "REPORT.md")
    if not summary["complete"]:
        return 1
    if args.agent in {"oracle", "nop", "tamper"}:
        expected = int(args.agent == "oracle")
        if any(row["success"] != expected for row in summary["trials"]):
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
