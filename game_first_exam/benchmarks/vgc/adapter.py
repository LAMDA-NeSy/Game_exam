"""Thin VGC adapter: one frozen battle against a fixed native opponent.

The native battle engine (poke-env + Pokemon Showdown) is kept unmodified. The
opponent is fixed at construction so the two-player game becomes a single-agent
episode: the agent submits its own joint action each turn and the adapter applies
the opponent's policy reply in the same native turn.

The agent sees only the serialized observation returned by `observe()`; the native
battle object and the Showdown websocket stay inside the trusted sim.
"""
import importlib.metadata
import json
from pathlib import Path

import numpy as np
from contracts import Capabilities, Transition
from encoding import state_hash

# One text action per turn. The exact joint-action grammar is game-specific and is
# validated by the adapter before it reaches the engine (see _encode_order).
ACTION_PATTERN = r"(?i)^(move|switch|terastallize)[^\r\n]{1,200}$"


def _native_env(instance, assets):
    """Build a native single-agent VGC battle against a fixed opponent.

    Uses poke-env's own async->sync bridge (DoublesEnv + SingleAgentWrapper) so the
    adapter stays synchronous, exactly as the training code in vgc_bench/src/env.py
    does. TODO(verify): confirm the fork's exact import paths and constructor args
    against the pinned commit.
    """
    from poke_env.environment import SingleAgentWrapper  # TODO(verify)
    from poke_env.player import (  # noqa: F401
        MaxBasePowerPlayer,
        RandomPlayer,
        SimpleHeuristicsPlayer,
    )
    from poke_env.ps_client import ServerConfiguration

    # The Showdown server runs in the same container on loopback; the agent cannot
    # reach it (isolation requirement).
    server = ServerConfiguration(
        "ws://127.0.0.1:7200/showdown/websocket",
        "https://play.pokemonshowdown.com/action.php?",
    )

    # DoublesEnv is the native VGC doubles environment exported by the fork.
    from poke_env.environment import DoublesEnv  # TODO(verify)

    env = DoublesEnv(
        server_configuration=server,
        battle_format=instance["battle_format"],
        team=instance["team1"],
        opponent=instance["team2"],
        start_challenging=False,
    )

    opponent_factory = {
        "random": RandomPlayer,
        "max_base_power": MaxBasePowerPlayer,
        "simple_heuristics": SimpleHeuristicsPlayer,
    }[instance["opponent_policy"]]
    opponent = opponent_factory(battle_format=instance["battle_format"])
    return SingleAgentWrapper(env, opponent)


class Adapter:
    def __init__(self, instance, assets=None):
        self.instance = instance
        for name, version in instance["engine_versions"].items():
            if importlib.metadata.version(name) != version:
                raise ValueError(f"engine version mismatch: {name}")
        self.env = _native_env(instance, assets)
        self.obs, self.info = self.env.reset(seed=instance["seed"])
        self.return_ = 0.0
        self.steps = 0
        self.ended = False

    def spec(self):
        return {
            "adapter_version": "1.0.0",
            "capabilities": Capabilities(images=False, action_mode="text", native_truncation=False).to_dict(),
            "action_schema": {"type": "string", "max_length": 200, "pattern": ACTION_PATTERN},
            "observation": "native VGC battle state serialized as JSON; see instruction.md",
            "opponent": self.instance["opponent_policy"],
            "format": self.instance["battle_format"],
        }

    def observe(self):
        # Serialize only player-visible battle state. TODO(verify): exact field
        # access against poke-env's DoubleBattle; never expose hidden engine state.
        return {
            "step": self.steps,
            "done": self.ended,
            "observation": _battle_to_dict(self.env),
        }

    def step(self, action):
        if self.ended:
            raise ValueError("episode closed")
        # TODO(verify): map the text action to the fork's native action format.
        self.obs, reward, terminated, truncated, self.info = self.env.step(action)
        self.steps += 1
        self.return_ += float(reward)
        self.ended = bool(terminated or truncated)
        return Transition(float(reward), bool(terminated), bool(truncated))

    def success(self):
        # TODO(verify): the fork's single-agent env exposes won/lost.
        return bool(getattr(self.env, "won", False))

    def metrics(self):
        win = int(self.success())
        return {
            "win": win,
            "completion_score": 100 * win,
            "native_return": self.return_,
            "native_steps": self.steps,
        }

    def fingerprint(self):
        # Deterministic initial state only: teams, ruleset and seed. The Showdown
        # engine PRNG is deliberately excluded (it is not seedable from Python).
        return state_hash({
            "reg": self.instance["reg"],
            "format": self.instance["battle_format"],
            "team1": self.instance["team1"],
            "team2": self.instance["team2"],
            "opponent_policy": self.instance["opponent_policy"],
            "seed": self.instance["seed"],
        })

    def frame(self):
        return None  # TODO(optional): render a transcript for the audit video

    def close(self):
        self.env.close()


def _battle_to_dict(env):
    """Player-visible battle state as JSON. TODO(verify) against poke-env."""
    return {"placeholder": "TODO_serialize_battle_state"}
