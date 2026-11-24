"""Check that the native Pac-Man opening and score advance in Chromium."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
GAME = ROOT.parent / "stack-review" / "benchmark" / "23_pacman"
sys.path[:0] = [str(ROOT / "game_first_exam/runtime"),
                str(ROOT / "game_first_exam/benchmarks/pacman")]

from adapter import Adapter  # noqa: E402


def main():
    if not GAME.is_dir():
        raise SystemExit(f"Native GameWorld source missing: {GAME}")
    # Adapter accepts a directory with a `game` child. Keep the source out of
    # the Game Exam repository so that the upstream rights notice stays intact.
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as temporary:
        (Path(temporary) / "game").symlink_to(GAME, target_is_directory=True)
        game = Adapter({}, temporary)
        try:
            print("Opening:", game.fingerprint(), game.state["status"], game.metrics())
            for action in ["left", "up", "right", "down"]:
                if game.done():
                    break
                game.step(action)
                print(action, game.state["status"], game.metrics())
        finally:
            game.close()


if __name__ == "__main__":
    main()
