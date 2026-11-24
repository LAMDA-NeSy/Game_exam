from game_client import GameClient

game = GameClient()
state = game.observe()
while not state["done"]:
    action = "boost_right" if state["step"] < 8 else "wait"
    state = game.step(action, expected_step=state["step"])
