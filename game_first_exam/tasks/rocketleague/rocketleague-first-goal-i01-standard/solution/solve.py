from game_client import GameClient

game = GameClient()
state = game.observe()
while not state["done"]:
    state = game.step("boost_right", expected_step=state["step"])
