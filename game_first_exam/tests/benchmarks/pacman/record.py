"""Record success and game-over examples from the unmodified game snapshot."""

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import imageio

ROOT = Path(__file__).resolve().parents[4]
GAME = ROOT.parent / "stack-review" / "benchmark" / "23_pacman"
TASK = ROOT / "game_first_exam/tasks/pacman/pacman-600-i01-standard"
sys.path[:0] = [str(ROOT / "game_first_exam/runtime"),
                str(ROOT / "game_first_exam/benchmarks/pacman")]

from adapter import Adapter  # noqa: E402


def record(assets, actions, filename):
    game = Adapter({}, assets)
    filename.parent.mkdir(parents=True, exist_ok=True)
    try:
        with imageio.get_writer(filename, fps=2, codec="libx264", quality=7) as video:
            video.append_data(game.frame())
            for action in actions:
                if game.done():
                    break
                game.step(action)
                video.append_data(game.frame())
        print(filename.name, game.fingerprint(), game.metrics(), flush=True)
        return game.metrics()
    finally:
        game.close()


def main():
    route = json.loads((TASK / "solution/route.json").read_text())
    with TemporaryDirectory(prefix="pacman-record-") as temporary:
        (Path(temporary) / "game").symlink_to(GAME, target_is_directory=True)
        dest = ROOT / "docs/demos/pacman"
        success = dest / "600-point-clear.mp4"
        if not record(temporary, route, success)["success"]:
            success.unlink(missing_ok=True)
            raise RuntimeError("Recorded route did not reach 600 points")
        failure = dest / "ghost-collision.mp4"
        metrics = record(temporary, ["right"] * 500, failure)
        if not metrics["deaths"]:
            failure.unlink(missing_ok=True)
            print("The failure example needs a different route", flush=True)


if __name__ == "__main__":
    main()
