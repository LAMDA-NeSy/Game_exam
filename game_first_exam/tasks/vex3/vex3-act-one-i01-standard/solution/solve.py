import json
from pathlib import Path
from game_client import GameClient

game = GameClient()
state = game.observe()
for move in json.loads(Path(__file__).with_name("route.json").read_text()):
    if state["done"]:
        break
    state = game.step(move, expected_step=state["step"])
