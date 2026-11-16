"""Frozen Baba Is AI engine; visible board only, with native reward/end semantics."""
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'vendor'))
import baba
import numpy as np
from contracts import Capabilities, Transition
from encoding import png, state_hash

COMMIT = '40ae1b29dbc67f2ecea06cc161ed5ca51719e5e3'
ACTIONS = {'idle': 0, 'up': 1, 'right': 2, 'down': 3, 'left': 4}


def native_state(env):
    """Audit all stack layers and behavioral state; never expose this to the player."""
    objects = [[None if obj is None else {'class': type(obj).__name__, **{
        key: value for key, value in vars(obj).items() if key not in {'_ruleset', 'img'}}}
        for obj in stack] for stack in env.grid.grid]
    return {'objects': objects, 'rules': env._ruleset.ruleset_dict,
            'agent_pos': env.agent_pos, 'agent_dir': env.agent_dir,
            'steps': env.step_count, 'won': bool(getattr(env, 'is_win', False)),
            'lost': bool(getattr(env, 'is_lose', False)), 'rng': env.np_random.bit_generator.state}


class Adapter:
    def __init__(self, instance, assets=None):
        self.instance = instance
        vendor = Path(__file__).resolve().parent / 'vendor'
        manifest = json.loads((vendor / 'SOURCE.json').read_text())
        if manifest['commit'] != instance['engine_commit'] or manifest['commit'] != COMMIT:
            raise ValueError('Baba source commit mismatch')
        for name, digest in manifest['files'].items():
            if hashlib.sha256((vendor / name).read_bytes()).hexdigest() != digest:
                raise ValueError('Baba source file mismatch: ' + name)
        for name, version in instance['engine_versions'].items():
            if importlib.metadata.version(name) != version:
                raise ValueError('Baba dependency version mismatch: ' + name)
        self.env = baba.make(instance['env_id'])
        if self.env.max_steps != instance['native_max_steps']:
            raise ValueError('native Baba step limit mismatch')
        self.env.reset(seed=instance['seed'])
        self.total_return = 0.0
        self.ended = False

    def spec(self):
        return {'adapter_version': '1.0.0',
                'capabilities': Capabilities(images=True, action_mode='enum', native_truncation=True).to_dict(),
                'action_schema': {'type': 'string', 'enum': list(ACTIONS)},
                'observation': 'Native RGB rendering of the board. No derived cell descriptions or parsed rules.',
                'actions': 'Absolute up/right/down/left move all YOU-controlled objects; idle is the native no-movement action.',
                'goal': 'Reach a native WIN condition by moving objects and rearranging rule words.'}

    def observe(self):
        return {'image_png_base64': png(self.frame())}

    def step(self, action):
        if self.ended:
            raise ValueError('episode closed')
        _, reward, done, _ = self.env.step(ACTIONS[action])
        terminated = bool(getattr(self.env, 'is_win', False) or getattr(self.env, 'is_lose', False))
        truncated = bool(self.env.step_count >= self.env.max_steps)
        if bool(done) != (terminated or truncated):
            raise ValueError('unexplained native done')
        self.total_return += float(reward)
        self.ended = bool(done)
        return Transition(float(reward), terminated, truncated)

    def success(self):
        return bool(getattr(self.env, 'is_win', False))

    def metrics(self):
        return {'success': int(self.success()), 'lost': int(bool(getattr(self.env, 'is_lose', False))),
                'native_return': self.total_return, 'native_steps': self.env.step_count,
                'native_max_steps': self.env.max_steps}

    def fingerprint(self):
        return state_hash(native_state(self.env))

    def frame(self):
        return np.asarray(self.env.render(mode='rgb_array', tile_size=32), dtype=np.uint8)

    def close(self):
        self.env.close()
