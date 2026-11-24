"""Find a native Pac-Man route locally, then replay it on untouched assets.

The temporary copy only exposes the game's existing state for route search.
The submitted task and the final replay use the original pinned game files.
"""

import json
import random
import shutil
import sys
from collections import deque
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[4]
GAME = ROOT.parent / "stack-review" / "benchmark" / "23_pacman"
sys.path[:0] = [str(ROOT / "game_first_exam/runtime"),
                str(ROOT / "game_first_exam/benchmarks/pacman")]

from adapter import Adapter  # noqa: E402

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
STATE = """() => {
  const game = window.__nativePacman;
  if (!game || !game.pacman || !game.map) return null;
  const tile = game.pacman.getTile();
  return {
    player: [tile.col, tile.row],
    direction: game.pacman.dir,
    ghosts: ['pinky', 'blinky', 'inky', 'sue'].map(name => {
      const ghost = game[name];
      if (!ghost) return null;
      const at = ghost.getTile();
      return [at.col, at.row, !!ghost._ghostFrightened];
    }).filter(Boolean),
    width: game.map.width,
    height: game.map.height,
    tiles: game.map.tiles.map(tile => [tile.col, tile.row, tile.code, !!tile.item]),
  };
}"""


def inspect(game):
    return game.page.evaluate(STATE)


def choose(state, rng, caution):
    x, y = state["player"]
    width, height = state["width"], state["height"]
    tiles = {(col, row): (code, item) for col, row, code, item in state["tiles"]}
    ghosts = [(gx, gy) for gx, gy, afraid in state["ghosts"] if not afraid]
    moves = []
    for action, (dx, dy) in DIRS.items():
        nxt = ((x + dx) % width, (y + dy) % height)
        if tiles.get(nxt, ("=", False))[0] in ("=", "h"):
            continue
        route = deque([(nxt, 1)])
        seen = {(x, y), nxt}
        distance = 40
        while route:
            node, steps = route.popleft()
            code, item = tiles.get(node, ("=", False))
            if item and code in (".", "*"):
                distance = steps - (2 if code == "*" else 0)
                break
            for sx, sy in DIRS.values():
                neighbor = ((node[0] + sx) % width, (node[1] + sy) % height)
                if neighbor not in seen and tiles.get(neighbor, ("=", False))[0] not in ("=", "h"):
                    seen.add(neighbor)
                    route.append((neighbor, steps + 1))
        danger = min((abs(nxt[0] - gx) + abs(nxt[1] - gy) for gx, gy in ghosts), default=99)
        score = -distance - caution * max(0, 5 - danger) + rng.uniform(-1.5, 1.5)
        if tiles[nxt][1]:
            score += 3
        moves.append((score, action))
    return max(moves)[1] if moves else "wait"


def episode(assets, index, caution):
    rng = random.Random(23 + index * 17)
    game = Adapter({}, assets)
    route = []
    try:
        opening = game.fingerprint()
        for step in range(240):
            state = inspect(game)
            if state is None:
                raise RuntimeError("Native game state was not exposed by the temporary probe")
            action = choose(state, rng, caution)
            route.append(action)
            game.step(action)
            if game.done():
                break
        print("trial", index, "opening", opening, "steps", len(route), "metrics", game.metrics(), flush=True)
        return route, game.metrics()
    finally:
        game.close()


def main():
    if not GAME.is_dir():
        raise SystemExit(f"Native game snapshot missing: {GAME}")
    with TemporaryDirectory(prefix="pacman-calibrate-") as root:
        source = Path(root) / "game"
        shutil.copytree(GAME, source)
        bundle = source / "bundle.js"
        original = bundle.read_text()
        marker = ";new(function(t)"
        if original.count(marker) != 1:
            raise RuntimeError("The pinned game's entry point changed")
        bundle.write_text(original.replace(marker, ";window.__nativePacman=new(function(t)", 1))
        best = ([], {"score": 0, "success": 0})
        for trial, caution in enumerate((1, 3, 0, 5, 2, 4, 6, 0)):
            route, metrics = episode(root, trial, caution)
            if metrics["score"] > best[1]["score"]:
                best = route, metrics
            if metrics["success"]:
                break
        print("Best exploratory score:", best[1], flush=True)
        if not best[1]["success"]:
            return
        # Verification uses the original source: only that replay can become a demo.
        bundle.write_text(original)
        dest = ROOT / "game_first_exam/tasks/pacman/pacman-600-i01-standard/solution/route.json"
        dest.unlink(missing_ok=True)
        game = Adapter({}, root)
        try:
            print("Unmodified opening:", game.fingerprint(), flush=True)
            for action in best[0]:
                if game.done():
                    break
                game.step(action)
            print("Unmodified replay:", game.metrics(), flush=True)
            if game.metrics()["success"]:
                dest.write_text(json.dumps(best[0], indent=2) + "\n")
                print("Route saved:", dest, flush=True)
        finally:
            game.close()
        if dest.is_file():
            from record import main as record_demos
            record_demos()


if __name__ == "__main__":
    main()
