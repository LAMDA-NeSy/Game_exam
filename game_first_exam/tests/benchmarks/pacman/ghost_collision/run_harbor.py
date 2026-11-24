import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    root = Path.cwd()
    prepare = root / "scripts/prepare_games.py"
    if not prepare.is_file():
        raise SystemExit("Run this script from the Game Exam repository root.")
    staging = root / "jobs/prepared"
    staging.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="pacman-ghost-collision-", dir=staging))
    config = run / "control.json"
    subprocess.run([sys.executable, str(prepare), "--suite", "pacman", "--output", str(config)],
                   check=True)
    rows = json.loads(config.read_text())["tasks"]
    if len(rows) != 1:
        raise RuntimeError("Expected one Vex 3 task.")
    task = Path(rows[0]["path"]).resolve()
    if not task.is_relative_to(run) or task.name != "pacman-600-i01-standard":
        raise RuntimeError("Expected a staged copy of Pac-Man 600 points.")
    shutil.copyfile(Path(__file__).with_name("solve.py"), task / "solution/solve.py")
    subprocess.run([sys.executable, str(root / "scripts/stamp_mtimes.py"), "--full", str(task)], check=True)
    subprocess.run(["harbor", "run", "-c", str(config), "-a", "oracle",
                    "--jobs-dir", str(root / "jobs"), "-y"], check=True)


if __name__ == "__main__":
    main()
