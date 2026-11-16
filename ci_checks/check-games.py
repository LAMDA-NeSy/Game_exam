#!/usr/bin/env python3
"""Validate all shipped game suites and frozen tasks without Docker or model calls."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import task_conventions as tc
from prepare_games import load_suite


def main():
    errors = tc.check_layout()
    if errors:
        raise ValueError("\n".join(errors))
    selected = set()
    for path in sorted((ROOT / "configs/game_suites").glob("*.toml")):
        suite, plans = load_suite(path.stem)
        selected.update(plans)
        print(f"{path.stem}: {len(plans)} tasks", flush=True)
    tasks = tc.iter_tasks()
    if selected != {p.name for p in tasks}:
        raise ValueError("Frozen tasks and suite union differ")
    load_suite("all")
    for args in ([sys.executable, "scripts/task_conventions.py", "--check", *map(str, tasks)],
                 [sys.executable, "scripts/files_image.py", "check"],
                 [sys.executable, "scripts/files_image.py", "digest"],
                 [sys.executable, "ci_checks/check-protocol.py", *map(str, tasks)],
                 [sys.executable, "ci_checks/check-resources.py", *map(str, tasks)],
                 [sys.executable, "ci_checks/check-monitor.py", "--tier", "invariants", *map(str, tasks)]):
        subprocess.run(args, cwd=ROOT, check=True)
    for task in tasks:
        for check in ("check-task-fields.sh", "check-task-structure.sh", "check-verifier-isolation.sh"):
            subprocess.run(["bash", f"ci_checks/{check}", str(task)], cwd=ROOT, check=True)
    print(f"PASS: {len(tasks)} frozen game tasks; all suites and shared bindings verified")


if __name__ == "__main__":
    main()
