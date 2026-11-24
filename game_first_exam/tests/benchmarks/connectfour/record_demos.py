"""Record readable win/loss previews from the frozen, scored native match."""

import json
import os
from pathlib import Path
import sys
import tempfile

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / folder) for folder in (
    "scripts", "game_first_exam/runtime", "game_first_exam/benchmarks/connectfour"
)]

from adapter import Adapter
from game_schemas import load_schema
from grade import grade
from metric_rules import validate_metrics
from server import Game


TASK = ROOT / "game_first_exam/tasks/connectfour/connectfour-match-i01-standard"
OUTPUT = ROOT / "docs/demos/connectfour"
INSTANCE = json.loads((TASK / "tests/instance.json").read_text())


def card(frame, title, subtitle):
    image = Image.new("RGB", (896, 864), (13, 18, 31))
    image.paste(Image.fromarray(frame), (2, 90))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=27)
    draw.text((16, 9), title, font=font, fill=(255, 255, 255))
    draw.text((16, 49), subtitle, font=ImageFont.load_default(size=21), fill=(180, 210, 250))
    return np.asarray(image)


def record(name, route_path, outcome, score):
    route = json.loads(route_path.read_text())
    with tempfile.TemporaryDirectory() as tmp:
        game = Game.open(Adapter, INSTANCE, None, tmp)
        frames = [(game.adapter.frame().copy(), "Empty board")]
        try:
            if game.adapter.fingerprint() != INSTANCE["initial_state_sha256"]:
                raise ValueError("Frozen native opening changed")
            for index, column in enumerate(route, 1):
                if game.final is not None:
                    break
                game.submit({"action": str(column), "expected_step": game.steps,
                             "request_id": f"demo-{index}"})
                frames.append((game.adapter.frame().copy(), f"Red move {index}: column {column}"))
            if game.final["metrics"]["outcome"] != outcome:
                raise ValueError("Unexpected native outcome")
            if grade(game.final, INSTANCE, validate_metrics)["primary_score"] != score:
                raise ValueError("The isolated verifier disagrees")
            if not (Path(tmp) / "replay.mp4").stat().st_size:
                raise ValueError("The native recorder failed")
        finally:
            game.close()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / name
    with imageio.get_writer(path, fps=6, codec="libx264", macro_block_size=16) as writer:
        for frame, label in frames:
            picture = card(frame, "CONNECT FOUR  |  Red vs Yellow", label)
            for _ in range(4):
                writer.append_data(picture)
        picture = card(frames[-1][0], "CONNECT FOUR  |  Red vs Yellow",
                       f"{outcome.upper()}  |  Red score: {score}  |  {len(route)} decisions")
        for _ in range(18):
            writer.append_data(picture)
    print(f"{path.name}: native {outcome}, score {score}, {len(route)} decisions, {path.stat().st_size} bytes")


if __name__ == "__main__":
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    load_schema("connectfour")
    record("red-win.mp4", TASK / "solution/route.json", "win", 1)
    record("red-loss.mp4", Path(__file__).with_name("loss") / "route.json", "loss", 0)
