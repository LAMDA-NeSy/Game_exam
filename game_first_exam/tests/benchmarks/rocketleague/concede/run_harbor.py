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
    run = Path(tempfile.mkdtemp(prefix="rocketleague-concede-", dir=staging))
    config = run / "control.json"
    subprocess.run([sys.executable, str(prepare), "--suite", "rocketleague", "--output", str(config)],
                   check=True)
    rows = json.loads(config.read_text())["tasks"]
    if len(rows) != 1:
        raise RuntimeError("Expected one Rocket League task.")
    task = Path(rows[0]["path"]).resolve()
    if not task.is_relative_to(run) or task.name != "rocketleague-first-goal-i01-standard":
        raise RuntimeError("Expected a staged copy of Rocket League first goal.")
    shutil.copyfile(Path(__file__).with_name("solve.py"), task / "solution/solve.py")
    subprocess.run([sys.executable, str(root / "scripts/stamp_mtimes.py"), "--full", str(task)], check=True)
    subprocess.run(["harbor", "run", "-c", str(config), "-a", "oracle", "-y"], check=True)


if __name__ == "__main__":
    main()
