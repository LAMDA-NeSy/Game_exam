"""Replay the opening of level one with Watergirl's first jump six inputs late."""
from game_client import GameClient


def main():
    game = GameClient()
    state = game.observe()
    # The winning route starts holding Watergirl's jump after input 18.
    # Keep moving for six more inputs before trying to jump.
    for count, action in ((24, "right/right"), (2, "right/jump_right"), (4, "right/right"),
                          (6, "jump_right/right"), (3, "right/right"), (2, "jump_right/right"),
                          (5, "jump_right/jump_right"), (1, "wait/jump_right"),
                          (9, "wait/wait"), (3, "left/left"), (6, "jump_left/jump_left"),
                          (100, "wait/wait")):
        for _ in range(count):
            if state["done"]:
                print(f"Native episode ended at step {state['step']}.")
                return
            state = game.step(action, expected_step=state["step"])
    if not state["done"]:
        raise RuntimeError("Expected the missed jump to end the episode.")


if __name__ == "__main__":
    main()
