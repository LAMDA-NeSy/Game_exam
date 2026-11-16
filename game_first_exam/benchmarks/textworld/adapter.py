"""Frozen native Z-machine games; expose selected player-visible text, never solution metadata."""
import hashlib
import importlib.metadata
import re
import textwrap
from pathlib import Path

import numpy as np
import textworld
from contracts import Capabilities, Transition
from encoding import state_hash
from PIL import Image, ImageDraw

# Keep native parser vocabulary; reject only interpreter controls and multi-command input.
ACTION_PATTERN = r"(?i)(?!\s*(?:q|g|noscript)(?:\s|$))(?!.*\b(?:then|again|restart|reset|undo|save|restore|quit|script|transcript|debug|print_state|print\s+state|restrict\s+commands|tw-[a-z-]+)\b)[^\r\n.;]{1,200}"


class Adapter:
    def __init__(self, instance, assets):
        self.instance = instance
        for name, version in instance["engine_versions"].items():
            if importlib.metadata.version(name) != version:
                raise ValueError(f"version mismatch: {name}")
        for filename, expected in instance["asset_sha256"].items():
            if Path(filename).name != filename:
                raise ValueError("invalid asset name")
            if hashlib.sha256((assets / filename).read_bytes()).hexdigest() != expected:
                raise ValueError(f"asset mismatch: {filename}")
        self.env = textworld.start(str(assets / "game.z8"), textworld.EnvInfos(
            description=True, inventory=True, objective=True, score=True, max_score=True,
            won=True, lost=True, moves=True))
        self.env.seed(instance["seed"])
        self.state = self.env.reset()
        self.score = float(self.state.score or 0)
        self.max_score = float(self.state.max_score)
        if self.score != 0 or self.max_score != instance["max_score"] or self.max_score <= 0:
            raise ValueError("unexpected starting score")
        self.calls = 0

    def spec(self):
        return {"adapter_version": "1.0.0", "capabilities": Capabilities(images=False, action_mode="text", native_truncation=False).to_dict(), "action_schema": {"type": "string", "max_length": 200,
                                  "pattern": ACTION_PATTERN},
                "observation": "native player feedback, room description, inventory and objective",
                "commands": "One native parser command per action; unknown commands reach the engine. All accepted commands, including look/inventory, consume one action.",
                "reset": "Interpreter control, undo, save/restore and debug commands are not in the action grammar."}

    def observe(self):
        # Do not forward GameState: it also contains the complete game, quests and possible solutions.
        return {key: self.state.get(key) or "" for key in ("feedback", "description", "inventory", "objective")}

    def step(self, action):
        previous = self.score
        self.state, cumulative_score, done = self.env.step(action)
        self.calls += 1
        self.score = float(cumulative_score)
        # TextWorld returns a cumulative score; convert it to a delta exactly once.
        return Transition(self.score - previous, bool(done), False)

    def success(self):
        return bool(self.state.won)

    def metrics(self):
        return {"score": self.score, "max_score": self.max_score,
                "normalized_score": self.score / self.max_score, "won": int(self.success()),
                "lost": int(bool(self.state.lost)), "native_moves": int(self.state.moves or 0)}

    def fingerprint(self):
        return state_hash({"assets": self.instance["asset_sha256"],
                           "interpreter": self.env.unwrapped._jericho.get_state(),
                           "score": self.score, "calls": self.calls,
                           "observation": self.observe()})

    def frame(self):
        # A transcript visualization of the live episode, not a synthetic gameplay screenshot.
        canvas = Image.new("RGB", (960, 640), (245, 246, 248))
        draw = ImageDraw.Draw(canvas)
        text = f"TextWorld | action {self.calls} | native score {self.score:g}/{self.max_score:g}\n\n"
        observation = self.observe()
        text += "\n\n".join(str(observation[key]) for key in ("objective", "feedback", "inventory"))
        text = re.sub(r"[^\x20-\x7e\n]", "?", text)
        lines = []
        for line in text.splitlines():
            lines.extend(textwrap.wrap(line, width=140) or [""])
        draw.multiline_text((20, 18), "\n".join(lines[:46]), fill=(20, 25, 35), spacing=3)
        return np.asarray(canvas)

    def close(self):
        self.env.close()
