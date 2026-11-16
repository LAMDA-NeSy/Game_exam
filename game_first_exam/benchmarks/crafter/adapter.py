"""Unmodified native Crafter environment; cached pixel observations and native metrics."""
import importlib.metadata

import crafter
import numpy as np
from contracts import Capabilities, Transition
from encoding import png, state_hash


class Adapter:
    def __init__(self, instance, assets=None):
        self.instance = instance
        for name, version in instance["engine_versions"].items():
            if importlib.metadata.version(name) != version:
                raise ValueError(f"version mismatch: {name}")
        self.env = crafter.Env(seed=instance["seed"])
        if self.env._length != instance['native_max_steps']:
            raise ValueError('native Crafter length mismatch')
        # Construct once and reset once: Crafter derives the native seed from (seed, episode number).
        self.image = self.env.reset()
        self.total_return = 0.0

    def spec(self):
        return {"adapter_version": "1.0.0", "capabilities": Capabilities(images=True, action_mode="enum", native_truncation=True).to_dict(), "action_schema": {"type": "string", "enum": list(self.env.action_names)},
                "observation": "Native 64x64 RGB image returned by reset/step, PNG transport only.",
                "achievement_names": list(self.env._player.achievements)}

    def observe(self):
        # Rendering consumes world RNG at night: return the cached native image.
        return {"image_png_base64": png(self.image)}

    def step(self, action):
        self.image, reward, done, info = self.env.step(self.env.action_names.index(action))
        self.total_return += float(reward)
        dead = info["discount"] == 0
        return Transition(float(reward), bool(done and dead), bool(done and not dead))

    def success(self):
        # An auxiliary, predeclared milestone for Harbor's binary compatibility output.
        # The benchmark's primary score is the complete achievement vector, not this boolean.
        return self.env._player.achievements[self.instance["milestone"]] > 0

    def metrics(self):
        achievements = {name: int(value > 0) for name, value in self.env._player.achievements.items()}
        return {"achievements": achievements, "achievement_count": sum(achievements.values()),
                "achievement_fraction": sum(achievements.values()) / len(achievements),
                "native_return": self.total_return, "health": int(self.env._player.health),
                "milestone_success": int(self.success())}

    def fingerprint(self):
        world = self.env._world
        objects = []
        for obj in world.objects:
            values = {}
            for key, value in vars(obj).items():
                if key in {"world", "random", "_player"}:
                    continue
                if isinstance(value, (str, int, float, bool, tuple, list, dict, np.ndarray)) or value is None:
                    values[key] = value
            objects.append({"type": type(obj).__name__, "values": values})
        return state_hash({"materials": world._mat_map, "object_map": world._obj_map,
                           "objects": objects, "rng": world.random.get_state(),
                           "step": self.env._step, "daylight": world.daylight,
                           "unlocked": sorted(self.env._unlocked)})

    def frame(self):
        return self.image

    def close(self):
        pass
