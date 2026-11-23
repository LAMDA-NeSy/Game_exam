"""Gymnasium 2048 backend with native RGB rendering and scoring."""
import importlib.metadata
import numbers

import gymnasium as gym
import gymnasium_2048  # noqa: F401 - registers the environment
import numpy as np

from contracts import Capabilities, Transition
from encoding import png, state_hash


ACTIONS = {'UP': 0, 'RIGHT': 1, 'DOWN': 2, 'LEFT': 3}
INFO_FIELDS = {'board', 'step_score', 'total_score', 'max', 'is_legal', 'illegal_count'}


def make_native_env(instance):
    return gym.make(
        instance['env_id'], render_mode='rgb_array',
        size=instance['board_size'], max_pow=instance['native_max_power'],
    )


class Adapter:
    def __init__(self, instance, assets=None):
        self.instance = instance
        for name, version in instance['engine_versions'].items():
            if importlib.metadata.version(name) != version:
                raise ValueError('2048 dependency version mismatch: ' + name)
        self.env = make_native_env(instance)
        try:
            native = self.env.unwrapped
            if (native.action_space.n != 4
                    or native.observation_space.shape != (
                        instance['board_size'], instance['board_size'],
                        instance['native_max_power'])):
                raise ValueError('native 2048 spaces changed')
            observation, info = self.env.reset(seed=instance['seed'])
            self._validate_native(observation, info, initial=True)
            self.image = self._render()
        except Exception:
            self.env.close()
            raise
        self.steps = 0
        self.total_return = 0.0
        self.ended = False

    def _validate_native(self, observation, info, initial=False):
        native = self.env.unwrapped
        size = self.instance['board_size']
        if (not isinstance(observation, np.ndarray)
                or observation.shape != (size, size, self.instance['native_max_power'])
                or observation.dtype != np.uint8
                or not np.all(observation.sum(axis=2) == 1)
                or not np.array_equal(np.argmax(observation, axis=2), native.board)):
            raise ValueError('native 2048 observation changed')
        if set(info) != INFO_FIELDS or not np.array_equal(info['board'], native.board):
            raise ValueError('native 2048 info changed')
        scalar_fields = ('step_score', 'total_score', 'max', 'illegal_count')
        if any(isinstance(info[key], bool) or not isinstance(info[key], numbers.Integral)
               for key in scalar_fields) or not isinstance(info['is_legal'], bool):
            raise ValueError('native 2048 info types changed')
        if (int(info['total_score']) != int(native.total_score)
                or int(info['step_score']) != int(native.step_score)
                or int(info['max']) != int(native.board.max())
                or int(info['illegal_count']) != int(native.illegal_count)
                or info['is_legal'] is not native.is_legal):
            raise ValueError('native 2048 info disagrees with engine state')
        if initial and ((native.board != 0).sum() != 2
                        or native.total_score != 0 or native.illegal_count != 0):
            raise ValueError('native 2048 initial state changed')

    def _render(self):
        image = self.env.render()
        if (not isinstance(image, np.ndarray)
                or list(image.shape) != self.instance['native_render_shape']
                or image.dtype != np.uint8):
            raise ValueError('native 2048 RGB rendering changed')
        return image.copy()

    def spec(self):
        return {
            'adapter_version': '1.0.0',
            'capabilities': Capabilities(images=True, action_mode='enum').to_dict(),
            'action_schema': {'type': 'string', 'enum': list(ACTIONS)},
            'action_indices': dict(ACTIONS),
            'observation': ('Native RGB rendering of the 4x4 board and cumulative score; '
                            'PNG transport only.'),
            'goal': 'Maximize the native merge score and build the largest possible tile.',
        }

    def observe(self):
        return {'image_png_base64': png(self.image)}

    def step(self, action):
        if self.ended:
            raise ValueError('episode closed')
        if action not in ACTIONS:
            raise ValueError('unknown 2048 action')
        observation, reward, terminated, truncated, info = self.env.step(ACTIONS[action])
        if isinstance(reward, bool) or not isinstance(reward, numbers.Integral) or reward < 0:
            raise ValueError('native 2048 reward changed')
        if truncated:
            raise ValueError('unexpected native 2048 truncation')
        self._validate_native(observation, info)
        reward = int(reward)
        if reward != int(info['step_score']):
            raise ValueError('native 2048 reward disagrees with step score')
        self.steps += 1
        self.total_return += reward
        if self.total_return != int(info['total_score']):
            raise ValueError('native 2048 cumulative score changed')
        self.image = self._render()
        self.ended = bool(terminated)
        return Transition(float(reward), bool(terminated), False)

    def success(self):
        return int(self.env.unwrapped.board.max()) >= self.instance['target_power']

    def metrics(self):
        native = self.env.unwrapped
        maximum = int(native.board.max())
        invalid = int(native.illegal_count)
        return {
            'target_reached': int(self.success()),
            'native_score': int(native.total_score),
            'max_tile': 2 ** maximum,
            'valid_moves': self.steps - invalid,
            'invalid_moves': invalid,
            'native_return': self.total_return,
        }

    def fingerprint(self):
        native = self.env.unwrapped
        return state_hash({
            'board': native.board,
            'rng': native.np_random.bit_generator.state,
            'step_score': native.step_score,
            'total_score': native.total_score,
            'is_legal': native.is_legal,
            'illegal_count': native.illegal_count,
            'steps': self.steps,
            'return': self.total_return,
            'ended': self.ended,
        })

    def frame(self):
        return self.image.copy()

    def close(self):
        self.env.close()
