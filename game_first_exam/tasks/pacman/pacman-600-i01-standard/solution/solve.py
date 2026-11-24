from game_client import GameClient

# A demonstration controller will be recorded after native browser validation.
game = GameClient()
state = game.observe()
for action in ["left", "up", "right", "down"]:
    if state["done"]:
        break
    state = game.step(action, expected_step=state["step"])
