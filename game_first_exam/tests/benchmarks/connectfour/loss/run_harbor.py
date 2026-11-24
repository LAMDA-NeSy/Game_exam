"""Run a losing policy against the same frozen native PettingZoo opponent."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    root = Path.cwd()
    if not (root / "scripts/prepare_games.py").is_file():
        raise SystemExit("Run from the Game Exam repository root")
    staging = root / "jobs/prepared"
    staging.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="connectfour-loss-", dir=staging))
    config = run / "control.json"
    subprocess.run([sys.executable, "scripts/prepare_games.py", "--suite", "connectfour",
                    "--output", str(config)], check=True)
    tasks = json.loads(config.read_text())["tasks"]
    if len(tasks) != 1:
        raise RuntimeError("Expected one Connect Four task")
    task = Path(tasks[0]["path"]).resolve()
    if not task.is_relative_to(run) or task.name != "connectfour-match-i01-standard":
        raise RuntimeError("The prepared task is not a frozen Connect Four match")
    shutil.copyfile(Path(__file__).with_name("route.json"), task / "solution/route.json")
    sys.path.insert(0, str(root / "scripts"))
    import task_conventions
    task_conventions.normalize(task)
    subprocess.run([sys.executable, "scripts/stamp_mtimes.py", "--full", str(task)], check=True)
    subprocess.run(["harbor", "run", "-c", str(config), "-a", "oracle",
                    "--jobs-dir", str(root / "jobs"), "--job-name", "connectfour-loss", "-y"], check=True)


if __name__ == "__main__":
    main()
