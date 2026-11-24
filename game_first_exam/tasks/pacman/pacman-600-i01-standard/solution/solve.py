import json
from pathlib import Path

from game_client import GameClient


game = GameClient()
state = game.observe()
route = json.loads(Path(__file__).with_name("route.json").read_text())
for action in route:
    if state["done"]:
        break
    state = game.step(action, expected_step=state["step"])
