"""Tetris Gymnasium backend using its native RGB observation wrapper."""
import importlib.metadata
import numbers

import gymnasium as gym
from tetris_gymnasium.envs import Tetris as _Tetris  # noqa: F401 - registers the environment
from tetris_gymnasium.wrappers.observation import RgbObservation

from contracts import Capabilities, Transition
from encoding import png, state_hash


ACTIONS = {
    'MOVE_LEFT': 0,
    'MOVE_RIGHT': 1,
    'MOVE_DOWN': 2,
    'ROTATE_CLOCKWISE': 3,
    'ROTATE_COUNTERCLOCKWISE': 4,
    'HARD_DROP': 5,
    'SWAP': 6,
    'NO_OP': 7,
}


def make_native_env(instance):
    native = gym.make(
        instance['env_id'], render_mode='rgb_array',
        width=instance['board_width'], height=instance['board_height'],
        gravity=instance['gravity'],
    )
    return RgbObservation(native)


class Adapter:
    def __init__(self, instance, assets=None):
        self.instance = instance
        for name, version in instance['engine_versions'].items():
            if importlib.metadata.version(name) != version:
                raise ValueError('Tetris dependency version mismatch: ' + name)
        self.env = make_native_env(instance)
        try:
            native = self.env.unwrapped
            if (native.width != instance['board_width']
                    or native.height != instance['board_height']
                    or native.gravity_enabled is not instance['gravity']
                    or native.queue.size != instance['native_queue_size']
                    or native.holder.size != instance['native_holder_size']):
                raise ValueError('native Tetris profile mismatch')
            image, _ = self.env.reset(seed=instance['seed'])
            expected_shape = (native.height_padded,
                              native.width_padded + native.queue.size * native.padding, 3)
            if image.shape != expected_shape or str(image.dtype) != 'uint8':
                raise ValueError('native Tetris RGB observation changed')
            self.image = image.copy()
        except Exception:
            self.env.close()
            raise
        self.total_return = 0.0
        self.lines_cleared = 0
        self.rewarded_placements = 0
        self.line_clear_score = 0
        self.ended = False

    def spec(self):
        return {
            'adapter_version': '1.0.0',
            'capabilities': Capabilities(images=True, action_mode='enum').to_dict(),
            'action_schema': {'type': 'string', 'enum': list(ACTIONS)},
            'action_indices': dict(ACTIONS),
            'observation': ('Native RGB observation containing the padded board, active piece, '
                            'four-piece preview queue and one-piece holder; PNG transport only.'),
            'goal': 'Clear lines and keep the native Tetris episode alive.',
        }

    def observe(self):
        return {'image_png_base64': png(self.image)}

    def step(self, action):
        if self.ended:
            raise ValueError('episode closed')
        if action not in ACTIONS:
            raise ValueError('unknown Tetris action')
        image, reward, terminated, truncated, info = self.env.step(ACTIONS[action])
        reward = float(reward)
        lines = info.get('lines_cleared')
        if isinstance(lines, bool) or not isinstance(lines, numbers.Integral):
            raise ValueError('invalid native line-clear count')
        lines = int(lines)
        if not 0 <= lines <= 4:
            raise ValueError('invalid native line-clear count')
        if terminated:
            if reward != 0:
                raise ValueError('native game-over reward changed')
        elif reward:
            expected = 1 + (lines ** 2) * self.instance['board_width']
            if reward != expected:
                raise ValueError('native placement reward changed')
            self.rewarded_placements += 1
            self.line_clear_score += (lines ** 2) * self.instance['board_width']
        self.image = image.copy()
        self.total_return += reward
        self.lines_cleared += lines
        self.ended = bool(terminated or truncated)
        return Transition(reward, bool(terminated), bool(truncated))

    def success(self):
        return self.lines_cleared >= self.instance['target_lines']

    def metrics(self):
        return {
            'success': int(self.success()),
            'lines_cleared': self.lines_cleared,
            'native_return': self.total_return,
            'rewarded_placements': self.rewarded_placements,
            'line_clear_score': self.line_clear_score,
        }

    def fingerprint(self):
        native = self.env.unwrapped
        randomizer = native.randomizer
        holder = [{'id': piece.id, 'matrix': piece.matrix}
                  for piece in native.holder.queue]
        return state_hash({
            'board': native.board,
            'active': {'id': native.active_tetromino.id,
                       'matrix': native.active_tetromino.matrix},
            'position': [native.x, native.y],
            'queue': list(native.queue.queue),
            'holder': holder,
            'bag': randomizer.bag,
            'bag_index': randomizer.index,
            'rng': randomizer.rng.bit_generator.state,
            'has_swapped': native.has_swapped,
            'game_over': native.game_over,
            'return': self.total_return,
            'lines_cleared': self.lines_cleared,
            'rewarded_placements': self.rewarded_placements,
            'line_clear_score': self.line_clear_score,
            'image': self.image,
        })

    def frame(self):
        return self.image.copy()

    def close(self):
        self.env.close()
