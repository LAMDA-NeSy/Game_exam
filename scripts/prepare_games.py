#!/usr/bin/env python3
"""Validate and stage game tasks as a native Harbor job config. Does not run agents."""

import argparse
import json
import shutil
import sys
import tomllib
from pathlib import Path

import files_image
import stamp_mtimes
import task_conventions as tc
from game_preflight import preflight

ROOT = Path(__file__).resolve().parents[1]


def load_suite(name):
    if name == "all":
        suites = [tomllib.loads(p.read_text()) for p in sorted((ROOT / "configs/game_suites").glob("*.toml"))]
        rows = {row["name"]: row for suite in suites for row in suite["tasks"]}
        suite = {"schema_version": "game-suite/2.1", "version": "1.0.0", "tier": "development",
                 "name": "games-all-v1.0.0", "files_images": sorted({x for s in suites for x in s["files_images"]}),
                 "tasks": [rows[n] for n in sorted(rows)]}
        return suite, preflight(suite)
    path = Path(name)
    if not path.is_file():
        path = ROOT / "configs/game_suites" / f"{name}.toml"
    suite = tomllib.loads(path.read_text())
    return suite, preflight(suite)


def select_tasks(suite, benchmarks=(), families=()):
    for field, values in (("benchmark", benchmarks), ("family", families)):
        if set(values) - {row[field] for row in suite["tasks"]}:
            raise ValueError(f"unknown {field}")
    selected = [
        row
        for row in suite["tasks"]
        if (not benchmarks or row["benchmark"] in benchmarks) and (not families or row["family"] in families)
    ]
    if not selected:
        raise ValueError("no tasks selected")
    return selected


def prepare(suite, plans, selected, output, *, tamper=False):
    output = Path(output).resolve()
    task_root = output.parent / (output.stem + ".tasks")
    if output.exists() or task_root.exists():
        raise ValueError("choose a new config path; prepared tasks must not be overwritten")
    for name in suite["files_images"]:
        files_image.build(name)
    output.parent.mkdir(parents=True, exist_ok=True)
    task_root.mkdir()
    tasks = []
    for row in selected:
        task = Path(stamp_mtimes.stage(str(plans[row["name"]][0]), str(task_root)))
        if tamper:
            shutil.copyfile(ROOT / "game_first_exam/tests/fixtures/game_tamper.sh", task / "solution/solve.sh")
            tc.normalize(task)
            stamp_mtimes.stamp_tree(str(task), full=True)
        tasks.append({"path": str(task), "source": row["benchmark"]})
    # Harbor owns job/model configuration, scheduling, logs, lock.json and result.json.
    # The caller layers a native agent config with -c (or explicitly overrides it with Harbor's CLI).
    config = {"tasks": tasks, "n_attempts": 1, "n_concurrent_trials": 1, "retry": {"max_retries": 0}}
    output.write_text(json.dumps(config, indent=2) + "\n")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", default="core")
    parser.add_argument("--benchmark", action="append", default=[])
    parser.add_argument("--family", action="append", default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    suite, plans = load_suite(args.suite)
    selected = select_tasks(suite, args.benchmark, args.family)
    if args.validate_only:
        print(f"Validated {len(plans)} tasks; selected {len(selected)}; no evaluation launched")
        return 0
    if args.output is None:
        parser.error("--output is required unless --validate-only")
    path = prepare(suite, plans, selected, args.output)
    print(f"Prepared {len(selected)} tasks: {path}")
    print("Run with harbor run -c <config> -c configs/harbor/oracle.json --plugin game_harbor:GameRecords")
    return 0


if __name__ == "__main__":
    sys.exit(main())
