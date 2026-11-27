"""Orchestrate the separately isolated, archive-based FightingICE league prototype."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
import zipfile

from competition_results import (
    DUEL_PLAYERS, SPEEDRUN_LOSS_FRAMES, SPEEDRUN_PROFILE, TRACKS, duel_report, duel_schedule,
    schedule, speedrun_report, summarize, verify_evidence,
)


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RELEASES = [
    ("DareFightingICE-7.1.zip", "510752a69a097b767677d3911b1407d6a08a721dad4faf2cb5b7a19b988f1c62"),
    ("resource-7.1.zip", "386fd713f901db00583054528ccfbce315953c157dc16231c4367416d86dce53"),
]
LIMIT = 64 * 1024 * 1024
BASE = "docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db"
ARCHIVE_PROFILE = "archive-based-v7.1-prototype"
DUEL_PROFILE = "duel-framedata-v1"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def outside_checkout(path):
    path = path.resolve()
    if path.is_relative_to(REPO):
        raise ValueError("place generated contexts and results outside the repository")
    return path


def install(destination, archives):
    for path, (name, digest) in zip(archives, RELEASES, strict=True):
        if sha(path) != digest:
            raise ValueError(f"official {name} SHA256 mismatch")
    destination.mkdir()
    for path, prefix in zip(archives, ("FightingICE7.1", ""), strict=True):
        with zipfile.ZipFile(path) as bundle:
            for member in bundle.infolist():
                relative = Path(member.filename)
                if relative.is_absolute() or ".." in relative.parts or stat.S_ISLNK(member.external_attr >> 16):
                    raise ValueError("unsupported member in pinned archive")
                if prefix:
                    relative = relative.relative_to(prefix)
                if member.is_dir():
                    continue
                if not relative.parts or relative.parts[0] not in {"data", "lib", "FightingICE.jar"}:
                    continue
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as out, bundle.open(member) as source:
                    shutil.copyfileobj(source, out)


def snapshot(source, target):
    """Stage plain source files, never mount the original submission directory."""
    if source.is_symlink() or not source.is_dir():
        raise ValueError("expected a controller directory, not a symlink")
    hashes, total = {}, 0
    target.mkdir()
    for folder, dirs, files in source.walk():
        if any((folder / name).is_symlink() for name in dirs):
            raise ValueError("symlinks are not permitted in a controller bundle")
        for name in sorted(files):
            path = folder / name
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("controller bundles may contain only regular files")
            total += info.st_size
            if total > LIMIT or len(hashes) >= 1024:
                raise ValueError("controller exceeds the Game Exam artifact limit")
            relative = path.relative_to(source)
            output = target / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, output)
            hashes[relative.as_posix()] = sha(output)
    if "controller.py" not in hashes:
        raise ValueError("missing controller.py")
    return hashes


def public_tables(resources, destination):
    if sha(resources) != RELEASES[1][1]:
        raise ValueError("official resource-7.1.zip SHA256 mismatch")
    with zipfile.ZipFile(resources) as bundle:
        for character, _, _ in TRACKS.values():
            character_dir = destination / character
            character_dir.mkdir(parents=True)
            for name in ("Motion.csv", "gSetting.txt"):
                (character_dir / name).write_bytes(bundle.read(f"data/characters/{character}/{name}"))


def dump(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def mount(source, target, readonly=True):
    if "," in str(source):
        raise ValueError("Docker bind paths may not contain commas")
    return ["--mount", f"type=bind,src={source},dst={target}" + (",readonly" if readonly else "")]


def docker(*args, **kwargs):
    return subprocess.run(["docker", *args], check=True, **kwargs)


def run_match(output, setup, engine, public, image, match, *, audio=True):
    output.mkdir()
    prefix = "game-exam-ftg-" + uuid.uuid4().hex[:12]
    isolated = ["--network", "none", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--user", f"{os.getuid()}:{os.getgid()}", "--read-only",
                "--pids-limit", "128", "--memory", "1g", "--cpus", "1",
                "--log-driver", "local", "--log-opt", "max-size=2m", "--log-opt", "max-file=2"]
    trusted_mounts = mount(engine, "/install") + mount(output, "/evidence", False)
    (output / "engine").mkdir()
    trusted_mounts += mount(output / "engine", "/engine", False)
    bridges = {}
    with tempfile.TemporaryDirectory(prefix="ftg-wire-") as temp, ExitStack() as cleanup:
        for side, name in enumerate((match["p1"], match["p2"]), 1):
            if name not in setup:
                continue
            directory = Path(temp) / str(side)
            directory.mkdir()
            bridges[side] = f"/p{side}/play.sock"
            trusted_mounts += mount(directory, f"/p{side}", False)
            worker = f"{prefix}-p{side}"
            cleanup.callback(subprocess.run, ["docker", "rm", "-f", worker],
                             check=False, capture_output=True, timeout=15)
            docker("run", "-d", "--name", worker, *isolated, "--tmpfs", "/tmp:rw,nosuid,nodev,noexec",
                   *mount(directory, "/wire"),
                   *mount(setup[name], "/submission"), *mount(public, "/app/moves"), "-e", "PYTHONPATH=/submission",
                   image, "python", "/bridge/competition_wire.py", "/wire/play.sock", str(side),
                   stdout=subprocess.DEVNULL, timeout=30)
        trusted = f"{prefix}-engine"
        cleanup.callback(subprocess.run, ["docker", "rm", "-f", trusted],
                         check=False, capture_output=True, timeout=15)
        try:
            docker("run", "--name", trusted, *isolated, "--tmpfs", "/tmp:rw,nosuid,nodev,exec",
                    "-e", "HOME=/tmp", "-e", "XDG_CACHE_HOME=/tmp/cache", *trusted_mounts, image, "python",
                    "/bridge/competition_match.py",
                    json.dumps(dict(match=match, bridges=bridges, audio=audio)), timeout=340)
            for side in bridges:
                if int(docker("wait", f"{prefix}-p{side}", capture_output=True, timeout=5).stdout) != 0:
                    raise ValueError(f"player {side} controller failed")
        finally:
            for side in bridges:
                with (output / f"p{side}-controller.log").open("wb") as log:
                    docker("logs", f"{prefix}-p{side}", stdout=log, stderr=subprocess.STDOUT, timeout=15)
    assessed = docker("run", "--rm", *isolated, *mount(output, "/evidence"), image,
                      "python", "/bridge/competition_results.py", "/evidence", json.dumps(match),
                      capture_output=True, text=True, timeout=30)
    return json.loads(assessed.stdout)


def stage_author(output, resources=None, *, track=None, league="standard"):
    output.mkdir(parents=True)
    (output / "environment").mkdir()
    (output / "tests").mkdir()
    instruction = (HERE / "competition_author.md").read_text()
    role = "Your controller should play both sides as GARNET (Rushdown) or NEZ (Zoning)."
    audio = ("Native `AudioData` is forwarded when the selected engine produces it; this task does "
             "not provide the tournament's generative sound setup.")
    scoring = ("Win a round by finishing with more remaining HP. A win earns one point, a draw earns "
               "half a point, and a loss earns zero. Total remaining HP breaks points ties.")
    if track:
        character, baseline, _ = TRACKS[track]
        role = f"Write one controller to play both sides as {character} ({track})."
        audio = "This task does not provide audio or screen callbacks."
        if league == "speedrun":
            style = "close-range pressure" if track == "rushdown" else "distance control"
            role += f" The opponent uses the same character and is controlled by {baseline}. Favor {style}."
            scoring = ("Minimize average scored frames across 30 rounds, playing five matches on each side. "
                       "A win or draw by remaining HP counts the native elapsed frames. "
                       f"A loss counts {SPEEDRUN_LOSS_FRAMES} frames. The ranking uses only the average scored frames.")
    (output / "instruction.md").write_text(
        instruction.replace("{{ROLE}}", role).replace("{{AUDIO}}", audio).replace("{{SCORING}}", scoring))
    shutil.copyfile(HERE / "requirements.txt", output / "environment/requirements.txt")
    if resources:
        public_tables(resources, output / "environment/moves")
    (output / "task.toml").write_text(
        'schema_version = "1.3"\nartifacts = ["/app/output/"]\n'
        '[task]\nname = "embodied-first-exam/fightingice-controller-authoring"\n'
        '[metadata]\ntask_type = "policy"\n'
        '[agent]\ntimeout_sec = 600\nnetwork_mode = "public"\n'
        '[verifier]\nenvironment_mode = "separate"\nnetwork_mode = "no-network"\n')
    (output / "environment/Dockerfile").write_text(
        f"FROM {BASE}\n"
        "RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources"
        " && apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install"
        " -y --no-install-recommends bash curl git nodejs npm ca-certificates && rm -rf /var/lib/apt/lists/*\n"
        "COPY requirements.txt /tmp/requirements.txt\n"
        "RUN pip install --timeout 90 --retries 5 --no-deps -r /tmp/requirements.txt && pip check && mkdir -p /app/output\n"
        + ("COPY moves /app/moves\n" if resources else "") + "WORKDIR /app\n")
    (output / "tests/Dockerfile").write_text(f"FROM {BASE}\nCOPY test.sh /tests/test.sh\n")
    verifier = output / "tests/test.sh"
    verifier.write_text(
        '#!/bin/bash\nset -eu\n'
        'if test -f /app/output/controller.py && test ! -L /app/output/controller.py'
        ' && PYTHONPYCACHEPREFIX=/tmp/author-cache python -m py_compile /app/output/controller.py; then\n'
        '  echo 1 > /logs/verifier/reward.txt\nelse\n  echo 0 > /logs/verifier/reward.txt\nfi\n')
    verifier.chmod(0o755)
    dump(output / "author-job.json", {"tasks": [{"path": str(output.resolve())}],
                                      "n_attempts": 1, "n_concurrent_trials": 1,
                                      "retry": {"max_retries": 0}})


def load_model_profile(path):
    profile = json.loads(path.read_text())
    if (not isinstance(profile, dict) or set(profile) - {"agents", "n_attempts", "n_concurrent_trials", "retry"}
            or profile.get("n_attempts", 1) != 1 or profile.get("n_concurrent_trials", 1) != 1
            or profile.get("retry", {"max_retries": 0}) != {"max_retries": 0}):
        raise ValueError(f"{path}: expected a single-agent profile with no job overrides or retries")
    agents = profile.get("agents")
    if not isinstance(agents, list) or len(agents) != 1 or not isinstance(agents[0], dict):
        raise ValueError(f"{path}: expected exactly one Harbor agent")
    agent = agents[0]
    if (set(agent) - {"name", "model_name", "kwargs"} or not agent.get("name")
            or not isinstance(agent["name"], str) or not isinstance(agent.get("kwargs", {}), dict)
            or not isinstance(agent.get("model_name", ""), str)):
        raise ValueError(f"{path}: use a native Harbor agent with name, model_name and optional kwargs")
    return {"agents": [agent]}


def load_native_profile(path):
    from harbor.agents.factory import AgentFactory

    profile = load_model_profile(path)
    if profile["agents"][0]["name"] not in AgentFactory.registered_names():
        raise ValueError(f"{path}: expected a built-in Harbor agent name")
    return profile


def author_controller(harbor, task, jobs, side, profile):
    with tempfile.TemporaryDirectory(prefix="ftg-profile-") as temp:
        config = Path(temp) / "agent.json"
        dump(config, profile)
        subprocess.run([harbor, "run", "-c", str(task / "author-job.json"), "-c", str(config),
                        "--jobs-dir", str(jobs), "--job-name", side, "-y", "--quiet"], check=True)
    job = jobs / side
    trials = list(job.glob("*/result.json"))
    if len(trials) != 1:
        raise ValueError(f"{side}: expected one Harbor trial; see {job}")
    result = json.loads(trials[0].read_text())
    agent = result.get("agent_info") or {}
    rewards = (result.get("verifier_result") or {}).get("rewards", {})
    if (result.get("exception_info") is not None or not result.get("finished_at")
            or result.get("verifier_environment_mode") != "separate" or rewards.get("reward") != 1
            or agent.get("name") != profile["agents"][0]["name"]):
        raise ValueError(f"{side}: Harbor did not produce a verified controller; see {job}")
    options = profile["agents"][0]
    return trials[0].parent / "artifacts/app/output", {
        "agent": agent["name"], "agent_version": agent.get("version"),
        "model_name": options.get("model_name"),
        "reasoning_effort": options.get("kwargs", {}).get("reasoning_effort"),
        "trial": str(trials[0].relative_to(jobs.parent)),
    }


def build_report(rows, results, provenance):
    profile = provenance["profile"]
    if profile == DUEL_PROFILE:
        return duel_report(rows, results, provenance["models"])
    if profile == SPEEDRUN_PROFILE:
        return speedrun_report(rows, results, provenance.get("models"))
    if profile == ARCHIVE_PROFILE:
        return {"partial_mcts_only": provenance["partial_mcts_only"], **summarize(rows, results)}
    raise ValueError("unknown competition profile")


def run_series(args, output, rows, sources, profiles=None):
    duel = args.command == "duel"
    speedrun = rows[0]["league"] == "speedrun"
    output.mkdir(parents=True)
    dump(output / "schedule.json", rows)
    bundle_dir = output / "controllers"
    bundle_dir.mkdir()
    if profiles:
        harbor = shutil.which("harbor") or str(Path(sys.executable).with_name("harbor"))
        if not Path(harbor).is_file():
            raise ValueError("install the repository's pinned Harbor dependency and activate its environment")
    if duel or speedrun:
        # Build from this checkout so a stale bridge image cannot forward audio.
        image = docker("build", "--quiet", "-f", str(HERE / "competition.Dockerfile"), str(HERE),
                       capture_output=True, text=True, timeout=900).stdout.strip()
    else:
        image = docker("image", "inspect", "--format", "{{.Id}}", args.image or "game-exam:fightingice-competition",
                       capture_output=True, text=True, timeout=30).stdout.strip()
    results = []
    with tempfile.TemporaryDirectory(prefix="ftg-engine-") as temp, ExitStack() as cleanup:
        pinned = "game-exam-ftg-run:" + uuid.uuid4().hex
        docker("image", "tag", image, pinned, timeout=30)
        cleanup.callback(subprocess.run, ["docker", "image", "rm", pinned],
                         check=False, capture_output=True, timeout=15)
        engine = Path(temp) / "engine"
        install(engine, [args.release, args.resources])
        public = Path(temp) / "moves"
        public_tables(args.resources, public)
        models, hashes, setup = {}, {}, {}
        if profiles:
            task = output / "author-task"
            stage_author(task, args.resources, track=args.track, league=rows[0]["league"])
            for side, profile in profiles.items():
                print(f"Authoring {side} with Harbor", flush=True)
                source, models[side] = author_controller(harbor, task, output / "author-jobs", side, profile)
                setup[side] = bundle_dir / side
                hashes[side] = snapshot(source, setup[side])
        else:
            setup = {name: bundle_dir / name for name in sources}
            hashes = {name: snapshot(Path(path), setup[name]) for name, path in sources.items()}
        provenance = {"release_sha256": dict(RELEASES), "image": image, "controller_sha256": hashes}
        if profiles:
            provenance["author_instruction_sha256"] = sha(task / "instruction.md")
            provenance["models"] = models
        if duel:
            provenance.update(profile=DUEL_PROFILE, track=args.track, pairs=args.pairs)
        elif speedrun:
            provenance.update(profile=SPEEDRUN_PROFILE, track=args.track, baseline=TRACKS[args.track][1])
        else:
            provenance.update(profile=ARCHIVE_PROFILE, partial_mcts_only=args.mcts_only,
                              organizer_source="operator-supplied; not authenticated" if args.organizer else None)
        dump(output / "provenance.json", provenance)
        for i, row in enumerate(rows, 1):
            match_dir = output / f"{i:04d}"
            if duel or speedrun:
                print(f"Match {i}/{len(rows)}: {row['p1']} (P1) vs {row['p2']} (P2)", flush=True)
            results.append(run_match(match_dir, setup, engine, public, pinned, row, audio=not (duel or speedrun)))
            dump(match_dir / "verified.json", results[-1])
    report = build_report(rows, results, provenance)
    report_path = output / ("duel-report.json" if duel else "league-report.json")
    dump(report_path, report)
    if duel or speedrun:
        print(json.dumps({"standings": report["standings"], "report": str(report_path)}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    author = sub.add_parser("author")
    author.add_argument("output", type=Path)
    author.add_argument("--resources", type=Path)
    duel = sub.add_parser("duel", help="author two frozen controllers with Harbor, then play side-swapped matches")
    duel.add_argument("--model-a", type=Path, required=True, metavar="PROFILE.json")
    duel.add_argument("--model-b", type=Path, required=True, metavar="PROFILE.json")
    duel.add_argument("--track", choices=TRACKS, default="rushdown")
    duel.add_argument("--pairs", type=int, default=1, help="P1/P2 swap pairs (two matches per pair)")
    duel.add_argument("--release", type=Path, required=True)
    duel.add_argument("--resources", type=Path, required=True)
    duel.add_argument("--output", type=Path, required=True)
    for verb in ("plan", "run", "summarize"):
        cmd = sub.add_parser(verb)
        if verb == "summarize":
            cmd.add_argument("output", type=Path)
            continue
        cmd.add_argument("--track", choices=TRACKS, required=True)
        cmd.add_argument("--league", choices=("standard", "style", "speedrun"), required=True)
        cmd.add_argument("--mcts-only", action="store_true")
        cmd.add_argument("entries", nargs="+" if verb == "plan" else "*", metavar="NAME=CONTROLLER_DIRECTORY")
        if verb == "run":
            cmd.add_argument("--model", type=Path, metavar="PROFILE.json",
                             help="author one speedrun controller with a native Harbor agent")
            cmd.add_argument("--release", type=Path, required=True)
            cmd.add_argument("--resources", type=Path, required=True)
            cmd.add_argument("--organizer", type=Path)
            cmd.add_argument("--image", help="runtime image for Standard and Style (default: game-exam:fightingice-competition)")
            cmd.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "author":
        stage_author(outside_checkout(args.output), args.resources)
        return
    if args.command == "duel":
        try:
            rows = duel_schedule(args.track, args.pairs)
            profiles = {name: load_native_profile(path)
                        for name, path in zip(DUEL_PLAYERS, (args.model_a, args.model_b), strict=True)}
        except (ValueError, OSError) as error:
            duel.error(str(error))
        run_series(args, outside_checkout(args.output), rows, {}, profiles)
        return
    if args.command == "summarize":
        rows = json.loads((args.output / "schedule.json").read_text())
        provenance = json.loads((args.output / "provenance.json").read_text())
        profile = provenance["profile"]
        if profile == DUEL_PROFILE:
            expected = duel_schedule(provenance["track"], provenance["pairs"])
        elif profile == SPEEDRUN_PROFILE:
            track = provenance["track"]
            if provenance["baseline"] != TRACKS[track][1]:
                raise ValueError("stored speedrun baseline does not match the track")
            expected = schedule(track, provenance["controller_sha256"], "speedrun")
        elif profile == ARCHIVE_PROFILE:
            if not rows or rows[0]["league"] not in ("standard", "style"):
                raise ValueError("stored league does not match the archive profile")
            names = [name for name in provenance["controller_sha256"] if name != "organizer"]
            expected = schedule(rows[0]["track"], names, rows[0]["league"], provenance["partial_mcts_only"])
        else:
            raise ValueError("unknown competition profile")
        if not rows or rows != expected:
            raise ValueError("stored match matrix does not match the frozen roster")
        results = []
        for i, row in enumerate(expected, 1):
            folder = args.output / f"{i:04d}"
            verified = folder / "verified.json"
            if not verified.is_file():
                raise ValueError(f"{folder.name}: missing verified match")
            parsed = verify_evidence(folder, row)
            if json.loads(verified.read_text()) != json.loads(json.dumps(parsed)):
                raise ValueError(f"{folder.name}: native CSV and verified result differ")
            results.append(parsed)
        print(json.dumps(build_report(rows, results, provenance), indent=2))
        return
    model = getattr(args, "model", None)
    if model and (args.league != "speedrun" or args.entries):
        parser.error("--model requires --league speedrun and replaces NAME=CONTROLLER_DIRECTORY")
    if not model and not args.entries:
        parser.error("supply a controller directory or a speedrun --model profile")
    if any("=" not in value or not value.split("=", 1)[1] for value in args.entries):
        parser.error("entries must be NAME=CONTROLLER_DIRECTORY")
    assignments = [value.split("=", 1) for value in args.entries]
    rows = schedule(args.track, ["entry"] if model else [name for name, _ in assignments],
                    args.league, args.mcts_only)
    if args.command == "plan":
        print(json.dumps(rows, indent=2))
        return
    if args.league == "speedrun":
        if args.organizer is not None or args.image is not None:
            parser.error("speedrun uses the track's MCTS and builds its runtime image from this checkout")
    elif (args.organizer is None) != args.mcts_only:
        parser.error("two-baseline schedule needs an operator-supplied --organizer controller; --mcts-only is explicitly partial")
    sources = dict(assignments)
    if args.organizer:
        sources["organizer"] = args.organizer
    try:
        profiles = {"entry": load_native_profile(model)} if model else None
    except (ValueError, OSError) as error:
        parser.error(str(error))
    run_series(args, outside_checkout(args.output), rows, sources, profiles)


if __name__ == "__main__":
    main()
