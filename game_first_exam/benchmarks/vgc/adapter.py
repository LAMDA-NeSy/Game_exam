"""Thin VGC adapter: one frozen battle against a fixed native opponent.

The native battle engine (poke-env fork + Pokemon Showdown) is kept unmodified. The
opponent is fixed at construction so the two-player game becomes a single-agent
episode: the agent submits its own joint action each turn and the adapter applies the
opponent's reply in the same native turn.

The agent sees only the serialized observation returned by `observe()`; the native
battle object and the Showdown websocket stay inside the trusted sim.

VERIFY (against the pinned poke-env fork, once it is installed): the DoublesEnv
constructor accepts a fixed `team` string (not just a RandomTeamBuilder), the
SingleAgentWrapper observation/action/reward surface, the joint-action encoding the
native env expects, and how a finished battle reports won/lost. These are the only
fork-specific touchpoints; the contract (spec/observe/step/success/metrics/fingerprint/
frame/close) and the below serialization are already in final shape.
"""
import importlib.metadata

from contracts import Capabilities, Transition
from encoding import state_hash

# One text action per turn: the joint doubles order (moves/switch/terastallize).
ACTION_PATTERN = r"(?i)^(move|switch|terastallize)[^\r\n]{1,200}$"


def _opponent_factory(policy):
    from poke_env.player import (  # noqa: F401
        MaxBasePowerPlayer,
        RandomPlayer,
        SimpleHeuristicsPlayer,
    )
    return {
        "random": RandomPlayer,
        "max_base_power": MaxBasePowerPlayer,
        "simple_heuristics": SimpleHeuristicsPlayer,
    }[policy]


class Adapter:
    def __init__(self, instance, assets=None):
        self.instance = instance
        for name, version in instance["engine_versions"].items():
            if importlib.metadata.version(name) != version:
                raise ValueError(f"engine version mismatch: {name}")

        from poke_env.environment import DoublesEnv, SingleAgentWrapper
        from poke_env.ps_client import ServerConfiguration

        # Showdown runs in the same container on loopback; the agent cannot reach it.
        server = ServerConfiguration(
            "ws://127.0.0.1:7200/showdown/websocket",
            "https://play.pokemonshowdown.com/action.php?",
        )
        env = DoublesEnv(
            server_configuration=server,
            battle_format=instance["battle_format"],
            accept_open_team_sheet=True,
            team=instance["team1"],
        )
        opponent_cls = _opponent_factory(instance["opponent_policy"])
        opponent = opponent_cls(battle_format=instance["battle_format"], team=instance["team2"])
        self.env = SingleAgentWrapper(env, opponent)
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
        return {"step": self.steps, "done": self.ended, "observation": self._state()}

    def step(self, action):
        if self.ended:
            raise ValueError("episode closed")
        self.obs, reward, terminated, truncated, self.info = self.env.step(action)
        self.steps += 1
        self.return_ += float(reward)
        self.ended = bool(terminated or truncated)
        return Transition(float(reward), bool(terminated), bool(truncated))

    def success(self):
        won = self.info.get("win") if isinstance(self.info, dict) else None
        return bool(won if won is not None else getattr(self.env, "won", False))

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
        return None

    def close(self):
        self.env.close()

    def _state(self):
        """Player-visible battle state, serialized from the poke-env battle object.

        Only the fields the agent is allowed to see are included (no hidden engine
        state). Field access mirrors poke-env's DoubleBattle; the exact attribute
        names are part of the fork verification above.
        """
        battle = getattr(self.env, "battle", self.env)
        active = getattr(battle, "active_pokemon", [])
        opponent_active = getattr(battle, "opponent_active_pokemon", [])

        def pokemon(p):
            return {
                "species": getattr(p, "species", None),
                "hp_fraction": getattr(p, "current_hp_fraction", None),
                "status": str(getattr(p, "status", None)),
                "ability": getattr(p, "ability", None),
                "item": getattr(p, "item", None),
                "moves": [m for m in getattr(p, "moves", {})],
            }

        return {
            "active": [pokemon(p) for p in active],
            "opponent_active": [pokemon(p) for p in opponent_active],
            "team": {k: pokemon(p) for k, p in getattr(battle, "team", {}).items()},
            "opponent_team": {k: pokemon(p) for k, p in getattr(battle, "opponent_team", {}).items()},
            "weather": str(getattr(battle, "weather", None)),
        }
