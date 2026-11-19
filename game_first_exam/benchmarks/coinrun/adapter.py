"""Single-episode Procgen CoinRun backend for the shared synchronous service."""
import importlib.metadata

import numpy as np
from procgen import ProcgenGym3Env

from contracts import Capabilities, Transition
from encoding import png, state_hash


ACTIONS = ('LEFT_DOWN', 'LEFT', 'LEFT_UP', 'DOWN', 'NOOP', 'UP',
           'RIGHT_DOWN', 'RIGHT', 'RIGHT_UP', 'D', 'A', 'W', 'S', 'Q', 'E')


class Adapter:
    def __init__(self, instance, assets=None):
        self.instance = instance
        for name, version in instance['engine_versions'].items():
            if importlib.metadata.version(name) != version:
                raise ValueError('CoinRun dependency version mismatch: ' + name)
        self.env = ProcgenGym3Env(
            num=1, env_name='coinrun', num_levels=1, start_level=instance['seed'],
            rand_seed=instance['seed'], num_threads=1,
            distribution_mode=instance['distribution_mode'],
            use_sequential_levels=False, paint_vel_info=False,
        )
        try:
            _, observations, first = self.env.observe()
            if not bool(first[0]):
                raise ValueError('CoinRun did not start at an episode boundary')
            self.image = observations['rgb'][0].copy()
        except Exception:
            self.env.close()
            raise
        self.total_return = 0.0
        self.steps = 0
        self.ended = False
        self.succeeded = False

    def spec(self):
        return {
            'adapter_version': '1.0.0',
            'capabilities': Capabilities(images=True, action_mode='enum').to_dict(),
            'action_schema': {'type': 'string', 'enum': list(ACTIONS)},
            'action_indices': dict(zip(ACTIONS, range(len(ACTIONS)))),
            'observation': 'Native 64x64 RGB image, transported as PNG. At the episode '
                           'boundary the last pre-action image is retained.',
            'goal': 'Collect the coin while avoiding lethal obstacles.',
        }

    def observe(self):
        return {'image_png_base64': png(self.image)}

    def step(self, action):
        if self.ended:
            raise ValueError('episode closed')
        index = ACTIONS.index(action)
        self.env.act(np.array([index], dtype=np.int32))
        rewards, observations, first = self.env.observe()
        reward = float(rewards[0])
        self.steps += 1
        self.total_return += reward
        self.ended = bool(first[0])
        if self.ended:
            # Gym3 returns the next episode's first image at this boundary.
            # Keep the prior image and inspect completion only inside the sim.
            self.succeeded = bool(self.env.get_info()[0]['prev_level_complete'])
        else:
            self.image = observations['rgb'][0].copy()
        # Gym3 supplies one episode-boundary flag. It does not distinguish a
        # death from its native timeout. Preserve this as a single native end.
        return Transition(reward, terminated=self.ended)

    def success(self):
        return self.succeeded

    def metrics(self):
        return {'success': int(self.succeeded), 'completion_score': 100 * int(self.succeeded),
                'native_return': self.total_return, 'native_steps': self.steps,
                'native_episode_ended': self.ended}

    def fingerprint(self):
        # Serialized engine state is audit-only and never enters observe/spec.
        # On termination this includes the native automatically reset state.
        return state_hash({'native_state': self.env.get_state(), 'image': self.image,
                           'steps': self.steps, 'return': self.total_return,
                           'ended': self.ended, 'success': self.succeeded})

    def frame(self):
        return self.image.copy()

    def close(self):
        self.env.close()
