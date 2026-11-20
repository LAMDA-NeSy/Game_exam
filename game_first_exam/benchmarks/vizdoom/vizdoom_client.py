"""ViZDoom action durations and continuous controls over the standard transport."""
from standard_game_client import GameClient as StandardGameClient, main
from vizdoom_actions import encode_action


class GameClient(StandardGameClient):
    def step(self, action, expected_step, request_id=None, *, tics=1, deltas=None):
        return super().step(encode_action(action, tics, deltas), expected_step, request_id)

    act = step


if __name__ == "__main__":
    main()
