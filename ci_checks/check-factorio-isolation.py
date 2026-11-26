"""Inspect two retained Harbor trials on an isolated Linux CI runner."""
import json
import re
import subprocess
import sys
from pathlib import Path


def containers(project):
    ids = subprocess.check_output(
        ["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}"], text=True
    ).split()
    assert ids, f"No containers for Compose project {project}"
    rows = json.loads(subprocess.check_output(["docker", "inspect", *ids]))
    services = {row["Config"]["Labels"]["com.docker.compose.service"]: row for row in rows}
    assert len(services) == len(rows), f"Duplicate service in {project}"
    return services


def volume(row, path, writable):
    mount, = [m for m in row["Mounts"] if m["Destination"] == path]
    assert mount["Type"] == "volume" and mount["RW"] is writable, path
    return mount["Name"]


def check(job):
    ids = set()
    volumes = set()
    starts, ends = [], []
    trials = sorted(job.glob("*/result.json"))
    assert len(trials) == 2, f"Expected two completed trials, got {len(trials)}"
    for path in trials:
        result = json.loads(path.read_text())
        assert result["exception_info"] is None and result["verifier_environment_mode"] == "separate"
        project = result["trial_name"].lower()
        runtime = containers(project + "__env")
        assert set(runtime) == {"main", "engine", "recorder"}
        verifier = containers(project + "__verifier__trial")
        assert set(verifier) == {"main"}
        agent, engine, recorder, grader = runtime["main"], runtime["engine"], runtime["recorder"], verifier["main"]
        for row in (agent, engine, recorder, grader):
            config = row["HostConfig"]
            assert not config["Privileged"] and config["PidMode"] != "host" and config["IpcMode"] != "host"
            for mount in row["Mounts"]:
                assert mount["Destination"] != "/var/run/docker.sock"
                if mount["Type"] == "bind":
                    source = Path(mount["Source"]).resolve()
                    assert source.name != "docker.sock" and not Path.cwd().is_relative_to(source)
                    if source.is_relative_to(Path.cwd()):
                        assert source.is_relative_to(path.parent.resolve()), f"Mount outside trial: {source}"
        for row in (engine, recorder, grader):
            assert row["HostConfig"]["NetworkMode"] == "none"
            assert not row["HostConfig"]["PortBindings"]
        for row in (engine, recorder):
            assert all(m["Type"] != "bind" for m in row["Mounts"])
        channel = volume(recorder, "/channel", True)
        bridge = volume(engine, "/tmp", True)
        assert volume(agent, "/channel", False) == channel
        assert volume(recorder, "/native", False) == bridge
        for row, hidden in ((agent, {bridge}), (engine, {channel}), (grader, {channel, bridge})):
            assert hidden.isdisjoint(m.get("Name") for m in row["Mounts"])
        assert bridge != channel and volumes.isdisjoint({bridge, channel}), "Cross-trial shared volume"
        volumes.update((bridge, channel))
        assert engine["State"]["Status"] == "exited"
        starts.append(engine["State"]["StartedAt"])
        ends.append(engine["State"]["FinishedAt"])

        trial = path.parent
        marker = (trial / "artifacts/logs/artifacts/fle-probe-id").read_text().strip()
        assert re.fullmatch(r"[0-9a-f]{32}", marker) and marker not in ids
        ids.add(marker)
        episode = json.loads((trial / "artifacts/evidence/episode.json").read_text())
        assert episode["sealed"] and episode["fault"] is None
        first, second = episode["steps"]
        assert first["code"].splitlines()[0] == f"trial_marker = '{marker}'"
        assert second["code"].strip() == "print(trial_marker)"
        assert [first["number"], second["number"]] == [1, 2]
        assert all(not s["error_occurred"] and s["reward"] == 0 for s in (first, second))
        rewards = json.loads((trial / "verifier/reward.json").read_text())
        assert rewards["iron_plate_goal_reached"] == 0 and "fle_inspect_score" in rewards
    assert max(starts) < min(ends), "Game engine lifetimes did not overlap"
    print("Two overlapping engines, four distinct volumes, two matching REPL readbacks and two isolated verifiers.")


if __name__ == "__main__":
    check(Path(sys.argv[1]))
