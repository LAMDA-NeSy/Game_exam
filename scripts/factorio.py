"""Run the pinned native FLE task with a Harbor agent."""
import fnmatch
import subprocess
import sys
import tomllib


def launch(root, include, exclude, limit, listing, args, harbor):
    task = root / "game_first_exam/benchmarks/factorio/iron_plate_throughput"
    name = task.name
    if (limit == 0 or (include and not any(fnmatch.fnmatchcase(name, p) for p in include))
            or any(fnmatch.fnmatchcase(name, p) for p in exclude)):
        print("No matching Factorio task", file=sys.stderr)
        return 2
    if listing:
        print(name)
        return 0
    spec = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))["metadata"]
    revision = spec["source_commit"]
    image = f"game-exam-fle:{revision}"
    upstream_image = f"game-exam-fle-upstream:{revision}"
    # Build the authors' Dockerfile against the exact matching remote tree.
    # Only the local image store is shared between trials.
    try:
        subprocess.run(["docker", "build", "-t", upstream_image, "-f", "fle/eval/inspect/sandbox/Dockerfile",
                        f'{spec["source"]}#{revision}'], check=True)
        subprocess.run(["docker", "build", "--build-arg", f"UPSTREAM_IMAGE={upstream_image}",
                        "-t", image, str(task.parent / "runtime")], check=True)
    except FileNotFoundError:
        print("Factorio requires Docker with Linux containers and Compose v2.", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    return harbor(["run", "-p", str(task), *args])
