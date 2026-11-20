"""Use the standard service with a deadline check inside long native actions."""
import time

import server


class ViZDoomSession(server.Game):
    def __init__(self, adapter, instance, output, wall_clock=600):
        super().__init__(adapter, instance, output, wall_clock)
        self.adapter.action_deadline_reached = self.action_deadline_reached

    def action_deadline_reached(self):
        return self.started is not None and time.monotonic() - self.started >= self.wall_clock


if __name__ == "__main__":
    # Select the session implementation in this simulator process. The protocol
    # handler, scenario lifecycle, collection and scoring remain shared.
    server.Game = ViZDoomSession
    server.main()
