"""Replay the paired inputs from a successful run of the frozen first level."""
import json
from pathlib import Path

from game_client import GameClient


def main():
    game = GameClient()
    observation = game.observe()
    route = json.loads(Path(__file__).with_name("route.json").read_text())
    for section in route:
        for count, action in section["moves"]:
            for _ in range(count):
                if observation["done"]:
                    print(f"Native episode ended after {observation['step']} paired actions.")
                    return
                observation = game.step(action, expected_step=observation["step"])
    if not observation["done"]:
        raise RuntimeError("Reference inputs ended before the native game finished.")
    print(f"Native episode ended after {observation['step']} paired actions.")


if __name__ == "__main__":
    main()
