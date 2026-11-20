"""Pin upstream assets at image build and prepare a private copy for each simulator."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
from urllib.request import urlopen
from zipfile import ZipFile


SOURCE = json.loads(Path(__file__).with_name("SOURCE.json").read_text())
ARCHIVE_SHA256 = SOURCE["files"]["linux.zip"]["sha256"]


def verify_asset(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != SOURCE["files"][path.name]["sha256"]:
        raise ValueError(f"unexpected TowerMind asset digest: {path.name}")


def download_assets(directory):
    directory.mkdir(parents=True, exist_ok=True)
    upstream = f"https://raw.githubusercontent.com/tb6147877/TowerMind/{SOURCE['commit']}"
    for name, description in SOURCE["files"].items():
        destination = directory / name
        if not destination.exists():
            with urlopen(f"{upstream}/{description['path']}", timeout=120) as response:
                with destination.open("wb") as stream:
                    shutil.copyfileobj(response, stream)
        verify_asset(destination)


def prepare_game(assets, workspace, instance):
    from instance_schema import DECISION_PERIOD

    archive = assets / "linux.zip"
    verify_asset(archive)
    verify_asset(assets / "wrappers.py")
    with ZipFile(archive) as bundle:
        bundle.extractall(workspace)
    directory = workspace / "linux"
    player = directory / "td.x86_64"
    player.chmod(0o700)
    configs = directory / "td_Data/StreamingAssets/Config"
    settings_path = configs / "EnvConfig.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    if settings["DecisionPeriod"] != DECISION_PERIOD:
        raise ValueError("unexpected native decision period")
    levels_path = configs / "BenchmarkLevelsConfig.json"
    levels = json.loads(levels_path.read_text(encoding="utf-8"))["Levels"]
    level, = (row for row in levels if row["ID"] == instance["level_id"])
    settings.update(
        GeneralizationLevel=0, LevelsConfigFileName=levels_path.name,
        # The pinned player cycles levels when IsAutoPlayLevels equals 1.
        RandomSeed=instance["seed"], IsAutoPlayLevels=0, IsRepeatFailingLevels=0,
        IsHumanPlayerPlaying=0, IsDrlReward=0, IsDebug=0, IsRecordingEnabled=0,
        IsOnlyPixelObs=1, NeedsNaturalLanguageObservation=0,
        NeedsRealtimeLanguageObservation=0,
    )
    settings_path.write_text(json.dumps(settings), encoding="utf-8")
    (configs / "FixedLevelsConfig.json").write_text(
        json.dumps({"CurrentLevel": instance["level_id"]}), encoding="utf-8"
    )
    return player, level["TotalLife"]


if __name__ == "__main__":
    download_assets(Path(sys.argv[1]))
