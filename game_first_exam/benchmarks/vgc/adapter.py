"""Thin VGC adapter: one frozen battle against a fixed native opponent.

The native battle engine (poke-env fork + Pokemon Showdown) is kept unmodified. The
opponent is fixed at construction so the two-player game becomes a single-agent
episode: the agent submits its own joint action each turn and the adapter applies the
opponent's reply in the same native turn.

The agent sees only the serialized observation returned by `observe()`; the native
battle object and the Showdown websocket stay inside the trusted sim.
"""
import importlib.metadata
import re
import textwrap

import numpy as np
from PIL import Image, ImageDraw

from contracts import Capabilities, Transition
from encoding import state_hash

# One joint doubles action per turn: two space-separated native action indices
# (each in [0, act_len)). The legal indices and their meanings are exposed in the
# observation (`available_moves`, `available_switches`, `can_tera`).
ACTION_PATTERN = r"^\d{1,3} \d{1,3}$"


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

        from gymnasium.spaces import Box
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
        opponent = opponent_cls(
            battle_format=instance["battle_format"],
            team=instance["team2"],
            server_configuration=server,
        )
        # poke-env's SingleAgentWrapper reads the PettingZoo-style dict that
        # vgc-bench's ShowdownEnv adds on top of DoublesEnv; supply a real Box
        # space for each agent (the adapter serves its own JSON observation).
        env.observation_spaces = {
            agent: Box(0, 1, shape=(1,), dtype=np.float32)
            for agent in env.possible_agents
        }
        self.env = SingleAgentWrapper(env, opponent)
        self.obs, self.info = self.env.reset(seed=instance["seed"])
        self.battle = self.env.env.battle1
        self.return_ = 0.0
        self.steps = 0
        self.ended = False

    def spec(self):
        return {
            "adapter_version": "1.0.0",
            "capabilities": Capabilities(images=False, action_mode="text", native_truncation=False).to_dict(),
            "action_schema": {"type": "string", "max_length": 20, "pattern": ACTION_PATTERN},
            "observation": "native VGC battle state serialized as JSON; see instruction.md",
            "opponent": self.instance["opponent_policy"],
            "format": self.instance["battle_format"],
        }

    def observe(self):
        return {"step": self.steps, "done": self.ended, "observation": self._state()}

    def step(self, action):
        if self.ended:
            raise ValueError("episode closed")
        parts = action.split()
        if len(parts) != 2 or not all(p.isdigit() for p in parts):
            raise ValueError("expected two space-separated action indices")
        joint = np.array([int(parts[0]), int(parts[1])], dtype=np.int64)
        self.obs, reward, terminated, truncated, self.info = self.env.step(joint)
        self.steps += 1
        self.return_ += float(reward)
        self.ended = bool(terminated or truncated)
        return Transition(float(reward), bool(terminated), bool(truncated))

    def success(self):
        return bool(self.battle.won)

    def metrics(self):
        win = int(self.success())
        return {
            "win": win,
            "completion_score": 100 * win,
            "native_return": self.return_,
            "native_steps": self.steps,
        }

    def fingerprint(self):
        # Deterministic initial battle state: both teams' species, moves, items,
        # abilities, types and tera types, plus turn/weather/fields. The Showdown
        # engine PRNG (damage rolls, speed ties) is excluded; it only unfolds after
        # the first action and is not seedable from Python.
        return state_hash(self._battle_state())

    def frame(self):
        """Audit-video transcript of the battle state; not an added observation."""
        state = self._state()

        def pkmn(p):
            if p is None:
                return "?"
            hp = f"{p['hp_fraction'] * 100:.0f}%" if p.get("hp_fraction") is not None else "?%"
            status = f" [{p['status']}]" if p.get("status") else ""
            item = p.get("item") or "no item"
            moves = "/".join(p.get("moves") or []) or "no moves"
            return f"{p['species']} {hp}{status} | {item} | {moves}"

        lines = [f"VGC | {self.instance['battle_format']} | turn {state['turn']} | step {self.steps}"]
        if state.get("won") is True:
            lines.append("RESULT: WON")
        elif state.get("lost") is True:
            lines.append("RESULT: LOST")
        if state.get("weather"):
            lines.append("Weather: " + ", ".join(state["weather"]))
        if state.get("fields"):
            lines.append("Fields: " + ", ".join(state["fields"]))
        lines += ["", "== YOUR ACTIVE =="] + [pkmn(p) for p in state["active"]]
        lines += ["", "== OPPONENT ACTIVE =="] + [pkmn(p) for p in state["opponent_active"]]
        lines += ["", "== YOUR TEAM =="] + [pkmn(p) for p in state["team"]]
        lines += ["", "== OPPONENT TEAM =="] + [pkmn(p) for p in state["opponent_team"]]

        text = re.sub(r"[^\x20-\x7e\n]", "?", "\n".join(lines))
        canvas = Image.new("RGB", (960, 640), (245, 246, 248))
        draw = ImageDraw.Draw(canvas)
        wrapped = []
        for line in text.splitlines():
            wrapped.extend(textwrap.wrap(line, width=130) or [""])
        draw.multiline_text((20, 18), "\n".join(wrapped[:46]), fill=(20, 25, 35), spacing=3)
        return np.asarray(canvas)

    def close(self):
        self.env.close()

    # ------------------------------------------------------------------ serialization

    def _pokemon(self, p):
        if p is None:
            return None
        return {
            "species": p.base_species,
            "hp_fraction": round(float(p.current_hp_fraction), 4),
            "status": p.status.name if p.status is not None else None,
            "ability": p.ability,
            "item": p.item,
            "moves": sorted(m.id for m in p.moves.values()),
            "types": sorted(t.name for t in p.types),
            "tera_type": p.tera_type.name if p.tera_type is not None else None,
            "fainted": bool(p.fainted),
        }

    def _team(self, team):
        states = [self._pokemon(p) for p in team.values() if p is not None]
        return sorted(states, key=lambda s: s["species"])

    def _battle_state(self):
        b = self.battle
        return {
            "turn": int(b.turn),
            "team": self._team(b.team),
            "opponent_team": self._team(b.opponent_team),
            "weather": sorted(w.name for w in b.weather),
            "fields": sorted(f.name for f in b.fields),
            "active": [self._pokemon(p) for p in b.active_pokemon],
            "opponent_active": [self._pokemon(p) for p in b.opponent_active_pokemon],
        }

    def _state(self):
        """Player-visible battle state plus the legal-action summary."""
        b = self.battle
        state = self._battle_state()
        state["won"] = b.won
        state["lost"] = b.lost
        state["available_moves"] = [[m.id for m in moves] for moves in b.available_moves]
        state["available_switches"] = [
            [p.base_species for p in switches] for switches in b.available_switches
        ]
        state["can_tera"] = list(b.can_tera)
        return state
