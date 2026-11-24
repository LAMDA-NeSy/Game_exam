"""Run the late-jump inputs in an isolated copy of the standard Harbor task."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def stage_control(task, adapter):
    shutil.copyfile(Path(__file__).with_name("solve.py"), task / "solution/solve.py")
    sim = task / "environment/sim"
    # The offline game has no rewarded-ad provider. Hide that menu item so the
    # native Game Over screen can finish opening after Watergirl dies.
    source = adapter.read_text()
    anchor = '        self.page.clock.run_for(4000)'
    if source.count(anchor) != 1:
        raise RuntimeError("Check the initialization point in the current Forest Temple adapter.")
    settings = '        self.page.evaluate("h5branding.Branding.analyticsEnabled = false")\n'
    (sim / "offline_adapter.py").write_text(source.replace(anchor, settings + anchor))
    with (sim / "Dockerfile").open("a") as stream:
        stream.write("\nCOPY offline_adapter.py /srv/adapter.py\n")


def main():
    root = Path.cwd()
    prepare = root / "scripts/prepare_games.py"
    if not prepare.is_file():
        raise SystemExit("Run this script from the Game Exam repository root.")
    staging = root / "jobs/prepared"
    staging.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="firewater-missed-jump-", dir=staging))
    config = run / "control.json"
    subprocess.run([sys.executable, str(prepare), "--suite", "firewater", "--output", str(config)],
                   check=True)
    rows = json.loads(config.read_text())["tasks"]
    if len(rows) != 1:
        raise RuntimeError("Expected one Forest Temple task.")
    task = Path(rows[0]["path"]).resolve()
    if not task.is_relative_to(run) or task.name != "firewater-forest-exit-i01-standard":
        raise RuntimeError("Expected a staged copy of Forest Temple level one.")
    stage_control(task, root / "game_first_exam/benchmarks/firewater/adapter.py")
    subprocess.run([sys.executable, str(root / "scripts/stamp_mtimes.py"), "--full", str(task)], check=True)
    subprocess.run(["harbor", "run", "-c", str(config), "-a", "oracle",
                    "--jobs-dir", str(root / "jobs"), "-y"], check=True)


if __name__ == "__main__":
    main()
