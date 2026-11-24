#!/usr/bin/env python3
"""Run one Harbor practice session and one fresh, held-out SlimeVolley match."""
import argparse
import hashlib
import json
import os
import secrets
import shutil
import stat
import subprocess
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "game_first_exam/tasks/slimevolley"
STANDARD = TASKS / "slimevolley-pixel-vs-baseline-i01-standard"
EXAM = ROOT / "game_first_exam/benchmarks/slimevolley"
PRACTICE_SEEDS = {"A": 2117382936, "B": 1056882141}
POLICY_SECONDS = 120
MAX_POLICY_BYTES = 256 * 1024


def docker(*args, **kwargs):
    return subprocess.run(["docker", *args], check=True, text=True, **kwargs)


def build(context, *options):
    return docker("build", "-q", *options, str(context), stdout=subprocess.PIPE).stdout.strip()


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def official_seed(path):
    if path is not None:
        seed = int(path.read_text().strip())
        if not 0 <= seed < 2**31 or seed in PRACTICE_SEEDS.values():
            raise ValueError("the official seed must be in [0, 2**31) and distinct from A and B")
        return seed
    seed = secrets.randbelow(2**31)
    while seed in PRACTICE_SEEDS.values():
        seed = secrets.randbelow(2**31)
    return seed


def stage_task(output, smoke):
    task = output / "slimevolley-practice"
    shutil.copytree(STANDARD, task, ignore=shutil.ignore_patterns("DIGEST", "README.md", "solution"))
    sim = task / "environment/sim"
    shutil.copyfile(EXAM / "exam_server.py", sim / "exam_server.py")
    with (sim / "Dockerfile").open("a") as file:
        file.write("\nCOPY exam_server.py /srv/exam_server.py\n")
    shutil.copyfile(EXAM / "practice.md", task / "instruction.md")
    config = task / "task.toml"
    header, metadata = config.read_text().split("[task]\n", 1)
    metadata = metadata.replace("slimevolley-pixel-vs-baseline-i01-standard", "slimevolley-practice")
    metadata = metadata.replace("Win the native pixel match against the built-in SlimeVolley opponent.",
                                "Practice native pixel matches and submit a standalone controller.")
    metadata = metadata.replace('protocol = "game-standard/2.2"', 'protocol = "slimevolley-exam/2"')
    metadata = metadata.replace("instance_seed = 2117382936\n", "").replace("/data/final.json", "/data/practice.json")
    if smoke:
        metadata = metadata.replace("timeout_sec = 600.0", "timeout_sec = 18.0")
    config.write_text(header.split("artifacts =", 1)[0] + """artifacts = [
  { source = "/var/rcb-monitor/", service = "rcb_monitor" },
  { source = "/data/practice.json", service = "sim" },
  "/app/output/",
]

[task]
""" + metadata)
    compose = task / "environment/docker-compose.yaml"
    compose.write_text(compose.read_text().replace("/srv/server.py", "/srv/exam_server.py practice"))
    tests = task / "tests/test.sh"
    tests.write_text(tests.read_text().split("python3 /tests/grade.py", 1)[0] +
                     'printf \'{"practice_collected": 1}\' > /logs/verifier/reward.json\n')
    if smoke:
        (task / "solution").mkdir()
        shutil.copy(EXAM / "smoke.sh", task / "solution/solve.sh")
    return task


def practice(output, task, config, hosts):
    command = ["harbor", "run", "-p", str(task), "-c", str(config), "-y",
               "--jobs-dir", str(output), "--job-name", "practice-job"]
    for host in hosts:
        command.extend(["--allow-agent-host", host])
    completed = subprocess.run(command)
    (trial_file,) = (output / "practice-job").glob("*/result.json")
    status = read_json(trial_file)
    error = status["exception_info"]
    timed_out = error is not None and error.get("exception_type") == "AgentTimeoutError"
    if (completed.returncode or error) and not timed_out:
        raise RuntimeError(f"Harbor practice failed; see {trial_file}")
    artifacts = trial_file.parent / "artifacts"
    summary = read_json(artifacts / "data/practice.json")
    if summary.keys() != PRACTICE_SEEDS.keys() or any(row["errors"] for row in summary.values()):
        raise RuntimeError("invalid simulator evidence in practice")
    return artifacts, summary, timed_out


def freeze_submission(artifacts, destination):
    folder = artifacts / "app/output"
    if any(path.is_symlink() for path in (artifacts, folder.parent, folder)):
        return "invalid", None, None
    for name in ("gen.py", "practice_gen.py"):
        candidate = folder / name
        try:
            fd = os.open(candidate, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            continue
        except OSError:
            return "invalid", None, None
        break
    else:
        return "missing", None, None
    with os.fdopen(fd, "rb") as file:
        if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
            return "invalid", None, None
        source = file.read(MAX_POLICY_BYTES + 1)
    if not source.strip() or len(source) > MAX_POLICY_BYTES:
        return "invalid", None, None
    try:
        compile(source, "gen.py", "exec")
    except (SyntaxError, ValueError, RecursionError):
        return "invalid", None, None
    destination.write_bytes(source)
    destination.chmod(0o444)
    return "submitted", hashlib.sha256(source).hexdigest(), name


def wait_for_sim(sim, marker, limit):
    deadline = time.monotonic() + limit
    while not marker.is_file():
        running = docker("inspect", "-f", "{{.State.Running}}", sim, stdout=subprocess.PIPE)
        if running.stdout.strip() != "true" or time.monotonic() >= deadline:
            docker("logs", "--tail", "40", sim)
            raise RuntimeError(f"simulator did not publish {marker.name}")
        time.sleep(0.25)


def rollout(official, sim_image, policy_image, grader_image, submitted):
    name = "slimevolley-exam-" + uuid4().hex[:10]
    sim, controller = name + "-sim", name + "-policy"
    evidence, grade = official / "evidence", official / "grade"
    evidence.mkdir()
    grade.mkdir()
    instance = official / "instance.json"
    docker("network", "create", "--driver", "bridge", "--internal",
           "--opt", "com.docker.network.bridge.gateway_mode_ipv4=isolated", name, stdout=subprocess.DEVNULL)
    outcome = {"status": submitted}
    try:
        docker("run", "-d", "--name", sim, "--network", name, "--network-alias", "sim",
               "--cpus", "1", "--memory", "1g", "--pids-limit", "128",
               "-v", f"{instance}:/srv/instance.json:ro", "-v", f"{evidence}:/data",
               sim_image, "python3", "/srv/exam_server.py", "official", stdout=subprocess.DEVNULL)
        wait_for_sim(sim, evidence / "server.pid", 30)
        if submitted == "submitted":
            available_env = ["GAME_URL=http://sim:8000", "HOME=/tmp", "PYTHONDONTWRITEBYTECODE=1"]
            available_env += [f"{prefix}_PROXY=" for prefix in ("HTTP", "HTTPS", "ALL", "NO")]
            available_env += [item.lower() for item in available_env[3:]]
            docker("run", "-d", "--name", controller, "--network", name, "--dns", "127.0.0.1",
                   "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                   "--user", "65534:65534", "--read-only", "--pids-limit", "256",
                   "--cpus", "1", "--memory", "1g", "--tmpfs", "/tmp:size=64m,mode=1777",
                   "--tmpfs", "/app/output:size=64m,mode=1777", "--log-opt", "max-size=4m",
                   *[arg for item in available_env for arg in ("-e", item)],
                   "-v", f"{official / 'gen.py'}:/app/gen.py:ro",
                   policy_image, "python3", "/app/gen.py", stdout=subprocess.DEVNULL)
            try:
                waited = docker("wait", controller, stdout=subprocess.PIPE, timeout=POLICY_SECONDS)
                code = int(waited.stdout.strip())
                outcome = {"status": "exited" if code == 0 else "failed", "exit_code": code}
            except subprocess.TimeoutExpired:
                stopped = subprocess.run(["docker", "kill", controller], capture_output=True)
                if stopped.returncode:
                    # A controller may exit on its own between docker wait and docker kill.
                    docker("wait", controller, stdout=subprocess.DEVNULL, timeout=10)
                outcome = {"status": "timeout"}
            with (official / "controller.log").open("w") as log:
                docker("logs", "--tail", "200", controller, stdout=log, stderr=log)

        docker("kill", "--signal", "USR1", sim, stdout=subprocess.DEVNULL)
        wait_for_sim(sim, evidence / "collection.ready", 90)
        docker("run", "--rm", "--network", "none",
               "-v", f"{instance}:/tests/instance.json:ro",
               "-v", f"{evidence}:/data:ro", "-v", f"{grade}:/logs/verifier",
               grader_image, "python3", "/tests/grade.py")
        metrics = read_json(grade / "metrics.json")
        steps = read_json(evidence / "rollout.json")
        if (metrics["reason"] not in {"native_terminated", "native_truncated", "step_limit"}
                or metrics["steps"] != steps["controller_steps"] + steps["idle_steps"]):
            raise RuntimeError("official match did not reach a valid game ending")
        return outcome, metrics, steps
    finally:
        for args in (("rm", "-f", controller, sim), ("network", "rm", name)):
            subprocess.run(["docker", *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new private exam output directory")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--agent-config", type=Path, help="Harbor JSON with one practice agent")
    mode.add_argument("--smoke", action="store_true", help="exercise the protocol with a local oracle")
    parser.add_argument("--allow-agent-host", action="append", default=[])
    parser.add_argument("--official-seed-file", type=Path, help="host-only file containing one integer")
    args = parser.parse_args()

    seed = official_seed(args.official_seed_file)
    source = read_json(args.agent_config or ROOT / "configs/harbor/oracle.json")
    (agent,) = source["agents"]
    output = args.output.resolve()
    output.mkdir(mode=0o700, parents=True)
    official = output / "official"
    official.mkdir(mode=0o700)
    config = output / "practice-config.json"
    # Keep only the caller's agent. The task owns the timeout, environment, and attempt count.
    config.touch(mode=0o600)
    write_json(config, {"agents": [agent], "n_attempts": 1, "n_concurrent_trials": 1,
                        "retry": {"max_retries": 0}})
    task = stage_task(output, args.smoke)

    sim = task / "environment/sim"
    sim_image = build(sim)  # Build before adding any practice instances.
    specs = docker("run", "--rm", "-i", "--network", "none", sim_image, "python3",
                   "/srv/exam_server.py", "instances",
                   input=json.dumps({**PRACTICE_SEEDS, "official": seed}),
                   stdout=subprocess.PIPE)
    instances = json.loads(specs.stdout)
    write_json(official / "instance.json", instances.pop("official"))
    write_json(sim / "practice-instances.json", instances)
    with (sim / "Dockerfile").open("a") as file:
        file.write("COPY practice-instances.json /srv/practice-instances.json\n")

    artifacts, summary, timed_out = practice(output, task, config, args.allow_agent_host)
    submitted, sha, submission_source = freeze_submission(artifacts, official / "gen.py")
    policy_image = build(STANDARD / "environment", "--target", "controller")
    outcome, metrics, steps = rollout(official, sim_image, policy_image,
                                      build(STANDARD / "tests"), submitted)
    if args.smoke and (not timed_out or submission_source != "practice_gen.py" or outcome["status"] != "exited"
                       or steps["controller_steps"] != 1 or steps["idle_steps"] <= 0
                       or summary["A"]["episodes"] != 2 or summary["B"]["episodes"] != 1):
        raise RuntimeError("smoke trial did not exercise both slots, the saved practice controller and idle completion")
    report = {"practice": summary, "practice_end": "time_limit" if timed_out else "agent_finished",
              "submission_source": submission_source, "submission_sha256": sha, "controller": outcome,
              "official": {**metrics, **steps}}
    write_json(output / "exam.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
