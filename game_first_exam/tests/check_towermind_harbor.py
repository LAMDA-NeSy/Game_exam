"""Run a disposable TowerMind trial through Harbor's Docker and separate verifier."""
import json
from pathlib import Path
import re
from shutil import copy2
import socket
import subprocess
import sys
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "game_first_exam/tests"
RUNTIME = ROOT / "game_first_exam/runtime"
BENCHMARK = ROOT / "game_first_exam/benchmarks/towermind"
SIM_IMAGE = "game-tests:towermind"
CLIENT_IMAGE = "game-tests:towermind-client"


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip(), encoding="utf-8", newline="\n")


def freeze_instance():
    # Run the same player, renderer and screen configuration as the Harbor simulator.
    code = """
import sys
sys.path.insert(0, 'game_first_exam/tests')
from towermind_fixture import instance
from adapter import Adapter
adapter = Adapter(instance())
try:
    print('Initial SHA256:', adapter.fingerprint())
finally:
    adapter.close()
"""
    run = subprocess.run(
        ["docker", "run", "--rm", "--init", "--network", "none", SIM_IMAGE,
         "xvfb-run", "-a", "-s", "-screen 0 1400x900x24", "python", "-c", code],
        check=True, stdout=subprocess.PIPE, text=True,
    )
    hashes = re.findall(r"^Initial SHA256: ([0-9a-f]{64})$", run.stdout, re.MULTILINE)
    if len(hashes) != 1:
        raise ValueError("expected the simulator's initial fingerprint")
    config = json.loads((TESTS / "fixtures/towermind-instance.json").read_text(encoding="utf-8"))
    config["initial_state_sha256"] = hashes[0]
    return json.dumps(config, indent=2) + "\n"


def stage_task(task, instance, endpoint):
    write(task / "instruction.md", """
        # TowerMind isolation smoke test

        Use the public GameClient to inspect the initial player frame and submit one command.
        This development check exercises Harbor's container and evidence boundaries.
    """)
    write(task / "task.toml", """
        schema_version = "1.3"
        artifacts = [{ source = "/data/final.json", service = "sim" }]

        [environment]
        build_timeout_sec = 300.0
        cpus = 2
        memory_mb = 2048
        storage_mb = 2048

        [agent]
        timeout_sec = 180.0
        network_mode = "public"

        [verifier]
        timeout_sec = 60.0
        environment_mode = "separate"
        network_mode = "no-network"

        [[verifier.collect]]
        service = "main"
        command = "kill -9 -1 2>/dev/null; exit 0"
        timeout_sec = 30

        [[verifier.collect]]
        service = "sim"
        command = "kill -USR1 $(cat /data/server.pid); i=0; while [ ! -f /data/collection.ready ] && [ $i -lt 30 ]; do sleep 1; i=$((i+1)); done; test -f /data/collection.ready && test -f /data/final.json"
        timeout_sec = 40
    """)
    write(task / "environment/docker-compose.yaml", """
        services:
          main:
            depends_on: [sim]
          sim:
            build:
              context: sim
              dockerfile: Dockerfile
    """)
    write(task / "environment/Dockerfile", f"""
        FROM {CLIENT_IMAGE}
        USER root
    """)
    write(task / "environment/sim/Dockerfile", f"""
        FROM {SIM_IMAGE}
        USER root
        RUN mkdir -p /srv /data && chown 65534:65534 /data \\
            && cp /repo/game_first_exam/runtime/*.py /repo/game_first_exam/benchmarks/towermind/*.py /srv/ \\
            && cp /repo/game_first_exam/benchmarks/towermind/SOURCE.json /srv/
        COPY instance.json /srv/instance.json
        USER 65534:65534
        WORKDIR /srv
        CMD ["xvfb-run", "-a", "-s", "-screen 0 1400x900x24", "python", "/srv/server.py"]
    """)
    write(task / "environment/sim/instance.json", instance)
    for directory in ("solution", "tests"):
        write(task / directory / "canary.py", f"ADDRESS = {endpoint!r}\n")
    write(task / "solution/solve.sh", """
        #!/bin/bash
        set -euo pipefail
        PYTHONPATH=/app:/solution python - <<'PY'
        from pathlib import Path
        import socket

        from canary import ADDRESS
        from towermind_probe import main

        with socket.create_connection(ADDRESS, timeout=3):
            print("Harbor agent reached the test listener on the runner.")

        for path in ("/tests", "/data/final.json", "/var/run/docker.sock",
                     "/logs/verifier/reward.json", "/logs/verifier/reward.txt"):
            assert not Path(path).exists(), f"agent can see private path: {path}"

        mountpoints = {line.split()[4] for line in Path("/proc/self/mountinfo").read_text().splitlines()}
        if "/logs/verifier" in mountpoints:
            print("Harbor exposes a verifier log mount to the agent; treat its contents as untrusted.")
        main()
        Path("/app/agent-marker").write_text("agent-only filesystem change")
        print("Harbor agent container isolation passed.")
        PY
    """)
    write(task / "tests/instance.json", instance)
    write(task / "tests/Dockerfile", """
        FROM docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
        COPY . /tests/
        RUN chmod +x /tests/test.sh
    """)
    write(task / "tests/test.sh", """
        #!/bin/bash
        set -euo pipefail
        # Harbor 0.23.0 mounts this output directory into the agent too.
        find /logs/verifier -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
        python /tests/check_isolation.py
        python /tests/grade.py
    """)
    write(task / "tests/check_isolation.py", """
        import json
        from pathlib import Path
        import socket

        from canary import ADDRESS

        try:
            connection = socket.create_connection(ADDRESS, timeout=3)
        except OSError:
            pass
        else:
            connection.close()
            raise AssertionError("offline verifier reached the test listener on the runner")
        assert not Path("/app/agent-marker").exists(), "verifier inherited the agent filesystem"
        evidence = json.loads(Path("/data/final.json").read_text())
        assert evidence["benchmark"] == "towermind" and evidence["result_valid"] is True
        assert evidence["steps"] == 1 and evidence["reason"] == "agent_finished"
        Path("/logs/verifier/isolation.txt").write_text(
            "Harbor separate verifier is offline, has a fresh filesystem and received sealed sim evidence.\\n"
        )
    """)
    for name in ("grade.py", "config_schema.py", "reducers.py"):
        copy2(RUNTIME / name, task / "tests" / name)
    for name in ("instance_schema.py", "metric_rules.py"):
        copy2(BENCHMARK / name, task / "tests" / name)


def main(workdir):
    task = workdir / "towermind-isolation"
    jobs = workdir / "jobs"
    instance = freeze_instance()
    job = jobs / "towermind-isolation"
    bridge = json.loads(subprocess.check_output(["docker", "network", "inspect", "bridge"], text=True))
    gateway = bridge[0]["IPAM"]["Config"][0]["Gateway"]
    # Keep a known-reachable TCP listener alive for both the agent and verifier checks.
    with socket.create_server((gateway, 0)) as listener:
        stage_task(task, instance, listener.getsockname())
        run = subprocess.run([
            "harbor", "run", "-p", str(task), "-c", str(ROOT / "configs/harbor/oracle.json"),
            "--jobs-dir", str(jobs), "--job-name", job.name, "-y",
        ])
    for pattern in ("*/agent/oracle.txt", "*/verifier/isolation.txt", "*/verifier/test-stdout.txt",
                    "*/verifier/test-stderr.txt", "*/trial.log"):
        for log in job.glob(pattern):
            print(f"{log.name}: {log.read_text(encoding='utf-8', errors='replace')[-3000:]}", flush=True)
    run.check_returncode()
    marker, = job.glob("*/verifier/isolation.txt")
    result = json.loads(marker.with_name("metrics.json").read_text(encoding="utf-8"))
    assert result["result_valid"] is True
    assert result["reason"] == "agent_finished" and result["steps"] == 1
    assert result["infra_error"] == 0 and result["primary_metric"] == "native_return"
    print("TowerMind passed the Harbor agent, simulator and verifier isolation checks.")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
