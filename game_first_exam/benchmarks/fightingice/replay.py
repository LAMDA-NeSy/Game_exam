"""Export verified FightingICE 7.1 matches to MP4 and a static replay manifest."""
import argparse
import json
import os
from pathlib import Path
import re
from struct import unpack_from
import subprocess
import sys
import tempfile

from competition import HERE, docker, dump, install, mount, outside_checkout, sha


REPLAY_IMAGE = "game-exam:fightingice-replay"
CHARACTER_IDS = {"GARNET": 0, "NEZ": 3}


def match_rounds(match):
    if "entry" in match:
        return match["rounds"]
    return [dict(round=n, p1_hp=hp1, p2_hp=hp2, elapsed_frames=frames)
            for n, hp1, hp2, frames in match["rounds"]]


def check_recording(replay, character, rounds):
    # The 7.1 HP-mode header has three int32s per player. Each frame then
    # contains two 20-byte player records. HP starts at byte 3 in each record.
    frames = sum(row["elapsed_frames"] for row in rounds)
    expected_size = 24 + frames * 40
    with replay.open("rb") as stream:
        data = stream.read(expected_size + 1)
    if (len(data) != expected_size
            or unpack_from(">6i", data) != (-1, 400, CHARACTER_IDS[character]) * 2):
        raise ValueError("replay size or character header disagrees with the verified match")
    end = 24
    for row in rounds:
        end += row["elapsed_frames"] * 40
        recorded = [max(0, unpack_from(">i", data, end - offset)[0]) for offset in (37, 17)]
        if recorded != [max(0, row["p1_hp"]), max(0, row["p2_hp"])]:
            raise ValueError(f"replay HP disagrees with verified round {row['round']}")


def render(replay, engine, destination, image, character, rounds):
    expected = [row["elapsed_frames"] for row in rounds]
    check_recording(replay, character, rounds)
    digest = sha(replay)
    with tempfile.TemporaryDirectory(dir=destination, prefix=".render-") as temp:
        work = Path(temp)
        with (destination / "render.log").open("wb") as log:
            try:
                docker("run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
                       "--security-opt", "no-new-privileges", "--user", f"{os.getuid()}:{os.getgid()}",
                       "--pids-limit", "128", "--cpus", "2", "--memory", "2g", "--shm-size", "128m",
                       "--tmpfs", "/tmp:rw,nosuid,nodev,exec",
                       *mount(engine, "/install"), *mount(replay, "/input/match.dat"),
                       *mount(work, "/out", False), image, character, stdout=log,
                       stderr=subprocess.STDOUT, timeout=275)
                engine_log = (work / "engine.log").read_text()
                durations = re.findall(r"Round Duration: .*?\(Expected (\d+\.\d+)\)", engine_log)
                if ([round(float(seconds) * 60) for seconds in durations] != expected
                        or "finished in the middle" in engine_log):
                    raise ValueError("native playback did not reproduce all verified round lengths")
                info = json.loads((work / "video.json").read_text())
                duration = float(info["format"]["duration"])
                if (info["streams"] != [{"codec_name": "h264", "width": 960, "height": 640}]
                        or duration < sum(expected) / 60):
                    raise ValueError("capture is missing or shorter than the verified match")
                (work / "poster.jpg").replace(destination / "poster.jpg")
                (work / "capture.mp4").replace(destination / "replay.mp4")
            finally:
                for filename in ("engine.log", "ffmpeg.log"):
                    if (work / filename).is_file():
                        (work / filename).replace(destination / filename)
    return dict(duration_seconds=round(duration, 2), native_replay_sha256=digest,
                video=f"{destination.name}/replay.mp4", poster=f"{destination.name}/poster.jpg")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="completed competition.py duel or speedrun output")
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--resources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new directory outside the checkout and run")
    parser.add_argument("--match", type=int, action="append", help="one-based match number, repeat to select several")
    args = parser.parse_args()

    run = args.run.resolve()
    output = outside_checkout(args.output)
    if output.is_relative_to(run):
        parser.error("place exports outside the scored run directory")
    report = json.loads(subprocess.check_output([sys.executable, str(HERE / "competition.py"),
                                                 "summarize", str(run)]))
    matches = report.get("matches")
    if not matches:
        parser.error("replay export requires a completed 7.1 duel or speedrun")
    selected = sorted(set(args.match or range(1, len(matches) + 1)))
    if any(i < 1 or i > len(matches) for i in selected):
        parser.error("match number is outside the verified schedule")
    image = docker("image", "inspect", "--format", "{{.Id}}", REPLAY_IMAGE,
                   capture_output=True, text=True, timeout=30).stdout.strip()
    output.mkdir(parents=True)
    manifest = {key: report[key] for key in ("track", "league", "mode", "baseline", "controllers", "standings")
                if key in report}
    manifest["models"] = {name: {field: model[field] for field in ("agent", "model_name", "reasoning_effort")
                                 if field in model}
                          for name, model in report.get("models", {}).items()}
    manifest.update(schema_version=1, renderer_image=image, matches=[])
    failed = False
    with tempfile.TemporaryDirectory(prefix="ftg-replay-") as temp:
        engine = Path(temp) / "engine"
        install(engine, [args.release, args.resources])
        for i in selected:
            directory = f"{i:04d}"
            target = output / directory
            target.mkdir()
            match = matches[i - 1]
            item = {**match, "id": i, "rounds": match_rounds(match)}
            try:
                replays = list((run / directory / "engine/log/replay").glob("*.dat"))
                if len(replays) != 1:
                    raise ValueError(f"expected one native replay for match {i}, found {len(replays)}")
                item.update(render(replays[0], engine, target, image, match["character"], item["rounds"]))
                item["status"] = "ready"
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                failed = True
                item.update(status="failed", error=str(error))
            manifest["matches"].append(item)
            pending = output / ".replays.json"
            dump(pending, manifest)
            pending.replace(output / "replays.json")
            print(f"Match {i}: {item['status']}", flush=True)
    print(output / "replays.json")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
