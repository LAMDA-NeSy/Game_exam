"""One column decision for Red, followed by one fixed Yellow response."""

import copy
from importlib.metadata import version

import numpy as np
from pettingzoo.classic import connect_four_v3

from contracts import Capabilities, Transition
from encoding import png, state_hash
from opponent import choose


RED, YELLOW = "player_0", "player_1"


class Adapter:
    def __init__(self, instance, assets=None):
        if version("pettingzoo") != instance["engine_version"]:
            raise ValueError("The pinned Connect Four version is not installed")
        self.instance = instance
        self.env = connect_four_v3.env(render_mode="rgb_array")
        try:
            self.env.reset(seed=instance["seed"])
            self.turns = []
            self.decisions = 0
            self.outcome = "playing"
            self.native_rewards = (0, 0)
            self.capture()
        except BaseException:
            self.env.close()
            raise

    def spec(self):
        return {"adapter_version": "1.0.0",
                "capabilities": Capabilities(True, "enum", native_truncation=True).to_dict(),
                "action_schema": {"type": "string", "enum": [str(i) for i in range(7)]},
                "goal": "Win a native Connect Four match as Red."}

    def board(self):
        return list(self.env.unwrapped.board)

    def legal(self, actor):
        return [int(column) for column in np.flatnonzero(self.env.observe(actor)["action_mask"])]

    def capture(self):
        frame = self.env.render()
        # The native 891-pixel board needs one padded pixel for H.264 recording.
        if frame.shape[1] % 2:
            frame = np.pad(frame, ((0, 0), (0, 1), (0, 0)), mode="edge")
        self.rgb = np.ascontiguousarray(frame)

    def observe(self):
        return {"image_png_base64": png(self.rgb),
                "board": [self.board()[row:row + 7] for row in range(0, 42, 7)],
                "legal_columns": [] if self.outcome != "playing" else self.legal(RED),
                "last_moves": copy.deepcopy(self.turns[-2:]),
                "outcome": self.outcome}

    def play(self, actor, column):
        if self.env.agent_selection != actor:
            raise RuntimeError("Unexpected Connect Four turn")
        legal = self.legal(actor)
        before = self.board()
        self.env.step(column)
        after = self.board()
        self.native_rewards = tuple(self.env.rewards[agent] for agent in (RED, YELLOW))
        if all(self.env.terminations.values()):
            self.outcome = ("illegal" if column not in legal else
                            "win" if self.native_rewards[0] == 1 else
                            "loss" if self.native_rewards[0] == -1 else "draw")
        self.turns.append({"actor": actor, "column": column, "board_before": before,
                           "board_after": after, "rewards": list(self.native_rewards)})

    def step(self, action):
        if self.outcome != "playing":
            raise ValueError("Match already ended")
        self.decisions += 1
        self.play(RED, int(action))
        reward = self.native_rewards[0]
        if self.outcome == "playing":
            response = choose(self.board(), self.legal(YELLOW), self.instance["opponent_seed"])
            self.play(YELLOW, response)
            reward += self.native_rewards[0]
        self.capture()
        return Transition(float(reward), self.outcome != "playing",
                          self.outcome == "illegal")

    def success(self):
        return self.outcome == "win"

    def metrics(self):
        return {"outcome": self.outcome, "success": int(self.success()),
                "native_rewards": list(self.native_rewards), "agent_decisions": self.decisions,
                "total_plies": len(self.turns), "final_board": self.board(),
                "moves": copy.deepcopy(self.turns)}

    def fingerprint(self):
        return state_hash({"board": self.board(), "turn": self.env.agent_selection,
                           "outcome": self.outcome, "seed": self.instance["seed"],
                           "opponent_seed": self.instance["opponent_seed"],
                           "policy": self.instance["opponent_policy"]})

    def frame(self):
        return self.rgb

    def close(self):
        self.env.close()
