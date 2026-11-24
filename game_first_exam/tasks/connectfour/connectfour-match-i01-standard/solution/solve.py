"""Replay a verified public Red route through the normal game client."""

import json
from pathlib import Path

from game_client import GameClient


game = GameClient()
state = game.observe()
for column in json.loads(Path("/solution/route.json").read_text()):
    if state["done"]:
        break
    if column not in state["observation"]["legal_columns"]:
        raise RuntimeError(f"Reference column {column} is full")
    state = game.step(str(column), expected_step=state["step"])

print("Native match:", state["observation"]["outcome"], "after", state["step"], "decisions")
