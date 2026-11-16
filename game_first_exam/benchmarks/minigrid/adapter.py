"""MiniGrid backend for the shared game service; legacy 1.1 runtime stays archived separately."""
import gymnasium as gym
import minigrid
from contracts import Capabilities, Transition
from encoding import state_hash
from minigrid.core.constants import COLOR_TO_IDX, OBJECT_TO_IDX, STATE_TO_IDX

ACTIONS = {"left": 0, "right": 1, "forward": 2, "pickup": 3, "drop": 4, "toggle": 5, "done": 6}


class Adapter:
    def __init__(self, instance, assets=None):
        self.instance = instance
        if minigrid.__version__ != instance["minigrid_version"] or gym.__version__ != instance["gymnasium_version"]:
            raise ValueError("simulator version mismatch")
        self.env = gym.make(instance["env_id"], render_mode="rgb_array")
        self.obs, _ = self.env.reset(seed=instance["seed"])
        if self.env.unwrapped.max_steps != instance["native_max_steps"]:
            raise ValueError("environment changed action budget")
        self.actions = {name: value for name, value in ACTIONS.items() if value < self.env.action_space.n}
        self.total_return, self.succeeded = 0.0, False

    def spec(self):
        return {"adapter_version": "1.0.0", "capabilities": Capabilities(images=False, action_mode="enum", native_truncation=True).to_dict(), "action_schema": {"type": "string", "enum": list(self.actions)},
                "observation": "egocentric 7x7; image[x][y]=[object,color,state]; agent at (3,6), facing y decreasing",
                "objects": OBJECT_TO_IDX, "colors": COLOR_TO_IDX, "states": STATE_TO_IDX,
                "directions": {"0": "east", "1": "south", "2": "west", "3": "north"},
                "see_through_walls": bool(self.env.unwrapped.see_through_walls)}

    def observe(self):
        # Serialize the native observation; do not derive extra state or add a wrapper.
        return {"mission": self.obs["mission"], "direction": int(self.obs["direction"]),
                "image": self.obs["image"].tolist()}

    def step(self, action):
        self.obs, reward, terminated, truncated, _ = self.env.step(self.actions[action])
        self.total_return += float(reward)
        self.succeeded = bool(terminated and self.total_return > 0)
        return Transition(float(reward), terminated, truncated)

    def success(self):
        return self.succeeded

    def metrics(self):
        return {"success": int(self.succeeded), "native_return": self.total_return}

    def fingerprint(self):
        u = self.env.unwrapped
        return state_hash({"grid": u.grid.encode().tolist(), "agent_pos": list(map(int, u.agent_pos)),
            "agent_dir": int(u.agent_dir), "carrying": None if u.carrying is None else list(u.carrying.encode()),
            "rng": u.np_random.bit_generator.state,
            "success_pos": list(map(int, u.success_pos)) if hasattr(u, "success_pos") else None,
            "failure_pos": list(map(int, u.failure_pos)) if hasattr(u, "failure_pos") else None,
            "obstacles": [list(map(int, obj.cur_pos)) for obj in getattr(u, "obstacles", [])]})

    def frame(self):
        return self.env.unwrapped.get_frame(tile_size=16)

    def close(self):
        self.env.close()
