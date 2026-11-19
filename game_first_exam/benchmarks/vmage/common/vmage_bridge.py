"""Single-episode bridge to unmodified V-MAGE native games.

Only the action loop is driven here. Native construction, init_run, physics,
rendering, scoring and frame-limit tests remain in externally installed source.
"""
import base64
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import shutil
import sys
import tempfile

from contracts import Capabilities, Transition

try:
    from .source_loader import verify_source, manifest
except ImportError:
    from source_loader import verify_source, manifest

_CONSTRUCTED = False
CLASSES = {'race': 'RaceGame', 'flappybird': 'FlappyBirdGame', 'pong': 'PongGame',
           'supermario': 'SuperMarioGame', 'tempestrun': 'TempestRunGame'}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class NativeAdapter:
    GAME = None

    def __init__(self, instance, assets=None):
        global _CONSTRUCTED
        if _CONSTRUCTED or 'utils.config' in sys.modules or 'game.pygame_base' in sys.modules:
            raise RuntimeError('V-MAGE requires exactly one native game construction per process')
        self.instance = instance
        if instance.get('native_game') != self.GAME:
            raise ValueError('native game identity mismatch')
        self.SCHEMA.validate(instance)
        if platform.python_version() != instance['python_version']:
            raise ValueError('native Python version mismatch')
        for name, expected in instance['engine_versions'].items():
            if importlib.metadata.version(name) != expected:
                raise ValueError('native dependency mismatch: ' + name)
        source = Path(os.environ.get('VMAGE_ROOT', '/opt/vmage')).resolve()
        metadata = verify_source(source)
        if metadata['source_manifest_sha256'] != instance['source_manifest_sha256']:
            raise ValueError('native manifest does not match frozen instance')
        # A private writable copy retains native relative paths without sharing
        # highscore/config or temporary screenshot files across episodes.
        self._previous_cwd = Path.cwd()
        self._temporary = tempfile.TemporaryDirectory(prefix='vmage-')
        self.root = Path(self._temporary.name)
        for relative in metadata['files']:
            dst = self.root / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, dst)
        os.chdir(self.root)
        sys.path.insert(0, str(self.root))
        if self.GAME == 'supermario':
            sys.path.append(str(self.root / 'game/supermario'))
        os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
        random.seed(instance['seed'])
        import numpy as np
        import pygame
        self.np, self.pygame = np, pygame
        np.random.seed(instance['seed'])
        pygame.init()
        pygame.display.set_mode((1, 1))
        if '.'.join(map(str, pygame.get_sdl_version())) != instance['sdl_version']:
            raise ValueError('native SDL version mismatch')
        from utils.config import Config
        config = Config()
        config.load_env_config(str(self.root / f'config/env_config/3steps/env_config_{self.GAME}_reasoning_3steps.json'))
        config.load_level_config(str(self.root / f"config/level_config/{self.GAME}game/level{instance['native_level']}.json"))
        config.FPS = instance['fps']
        self._output = self.root / 'frames'
        self._output.mkdir()
        cls = getattr(importlib.import_module('game.' + self.GAME + '_game'), CLASSES[self.GAME])
        _CONSTRUCTED = True
        self.env = self.game = cls(str(self._output))
        if self.env.sample_frames != instance['frames_per_decision'] or self.env.action_in_sample_frames != instance['passive_action']:
            raise ValueError('effective native action sampling mismatch')
        if list(self.env.valid_actions) != instance['native_actions']:
            raise ValueError('native action inventory mismatch')
        if list(self.env.screen.get_size()) != instance['surface_size']:
            raise ValueError('native surface size mismatch')
        effective_limit = getattr(self.env, 'max_rounds', getattr(self.env, 'max_round', None))
        if effective_limit == -1:
            effective_limit = None
        if effective_limit != instance['native_frame_limit']:
            raise ValueError('native frame limit mismatch')
        self.decisions = 0
        self.native_step_calls = 1
        self.native_frames_advanced = 0
        self.terminated = self.truncated = False
        self.terminal_cause = 'running'
        self._closed = False
        self.env.init_run()  # Native step('None', 0), capture, frame ledger and history.
        if self.env.over or float(self.env.score) != 0 or len(self.env.game_frames) != 1:
            raise ValueError('unsupported nonzero or terminal initialization')
        self.initial_score = float(self.env.score)
        self._cache()

    def _cache(self):
        # No render call: native render mutates Race collisions and Tempest RNG.
        self._image_png = self.env.last_frame_base64
        self._frame = self.pygame.surfarray.array3d(self.env.screen).transpose(1, 0, 2).copy()
        self._frame.setflags(write=False)
        # Keep the native list and count, but bound actual screenshot disk usage.
        for path in self._output.glob('*.png'):
            path.unlink()

    def _capture(self):
        from utils.game_utils import capture
        path, encoded = capture(self.env.screen, self.env.output_dir)
        self.env.last_frame_path = path
        self.env.last_frame_base64 = encoded
        self.env.game_frames.append(path)

    def spec(self):
        return {'adapter_version': '1.0.0',
                'capabilities': Capabilities(images=True, action_mode='enum', native_truncation=self.GAME in {'race', 'supermario'}).to_dict(),
                'action_schema': {'type': 'string', 'enum': list(self.env.valid_actions)},
                'observation': 'Cached native screenshot, pygame.transform.scale to height 360; PNG only.',
                'frames_per_decision': self.env.sample_frames, 'passive_action': self.env.action_in_sample_frames,
                'native_dt': 0.033, 'native_fps': 30,
                'recording': 'Decision-frame samples of cached native RGB; not a complete 30 FPS replay.'}

    def observe(self):
        return {'image_png_base64': self._image_png}

    def step(self, action):
        if self._closed or self.env.over:
            raise ValueError('native episode is closed or terminal')
        if action not in self.env.valid_actions:
            raise ValueError('invalid native action')
        before = float(self.env.score)
        self.decisions += 1
        for frame in range(self.env.sample_frames):
            self.env.clock.tick(30)
            step_action = action if frame == 0 or self.env.action_in_sample_frames is None else self.env.action_in_sample_frames
            ledger_before = len(self.env.game_frames)
            limit = self.instance['native_frame_limit']
            hit_limit = limit is not None and ledger_before >= limit
            done, info = self.env.step(step_action, 0.033)
            self.native_step_calls += 1
            # Race checks its cap before any state update. Mario checks after.
            if not (self.GAME == 'race' and hit_limit):
                self.native_frames_advanced += 1
            if self.GAME == 'race':
                terminal = bool(done and not hit_limit)
                cause = 'native_win' if self.env.win_condition else 'native_collision'
            elif self.GAME == 'supermario':
                terminal = bool(self.env.mario.restart)
                cause = 'native_death'
            else:
                terminal = bool(done)
                cause = 'native_death' if self.GAME != 'pong' else 'native_missed_paddle'
            if done:
                self.terminated = terminal
                self.truncated = bool(hit_limit)
                self.terminal_cause = ('native_frame_limit+' + cause if hit_limit and terminal else 'native_frame_limit' if hit_limit else cause)
            # PygameBase captures even terminal first actions. Passive terminal
            # frames break BEFORE capture; this asymmetry affects native caps.
            if frame == 0:
                self.env.history_frame_base64 = self.env.last_frame_base64
                self.env.history_action = action
                self.env.history_valid_action = action
                self.env.history_action_info = info
                self._capture()
            elif not done:
                self.env.history_action_info = info
                self._capture()
            if done:
                break
        self._cache()
        return Transition(float(self.env.score) - before, self.terminated, self.truncated)

    def success(self):
        return bool(self.env.win_condition) if self.GAME == 'race' else bool(self.env.score > 0)

    def metrics(self):
        score = float(self.env.score)
        result = {'native_score': score, 'initial_native_score': self.initial_score,
                  'native_frame_count': len(self.env.game_frames),
                  'native_step_calls': self.native_step_calls,
                  'native_frames_advanced': self.native_frames_advanced,
                  'native_initialization_calls': 1, 'decision_count': self.decisions,
                  'native_invalid_action_count': int(self.env.invalid_action_count),
                  'native_terminated': self.terminated, 'native_truncated': self.truncated,
                  'terminal_cause': self.terminal_cause,
                  'native_frame_limit': self.instance['native_frame_limit'],
                  'visual_wallclock_dependency': self.GAME == 'tempestrun'}
        if self.GAME == 'race':
            from game.race.utils import get_distance
            result.update(native_win=bool(self.env.win_condition), native_completion_degree=max(0, self.env.origin_distance - get_distance(self.env.car, self.env.trophy)) / self.env.origin_distance)
        elif self.GAME == 'pong':
            result.update(score_a=self.env.scoreA, score_b=self.env.scoreB)
        elif self.GAME == 'flappybird':
            result.update(pipe_pair_score=score, counted_live_pipe_halves=sum(int(p['counted']) for p in self.env.pipe_list))
        elif self.GAME == 'supermario':
            result.update(dashboard_points=self.env.dashboard.points, dashboard_coins=self.env.dashboard.coins, dashboard_ticks=self.env.dashboard.ticks, dashboard_time=self.env.dashboard.time, mario_restart=bool(self.env.mario.restart))
        else:
            player = self.env.current_mode.player
            result.update(distance_z=player.z, player_dead=bool(player.is_dead()), player_mode=player.current_mode)
        return result

    def _freeze(self, value, seen=None, path='state'):
        """Serialize native state fields, excluding resources and visual timestamps.

        Stable graph paths replace references; no repr, address, event, or clock is
        admitted. This audit snapshot is not a restorable engine checkpoint.
        """
        seen = {} if seen is None else seen
        if value is None or type(value) in (str, int, float, bool):
            return value
        if isinstance(value, self.np.ndarray):
            return value.tolist()
        if isinstance(value, self.np.generic):
            return value.item()
        if isinstance(value, (self.pygame.Rect, self.pygame.Vector2, self.pygame.Vector3, self.pygame.Color)):
            return list(value)
        if isinstance(value, (list, tuple)):
            return [self._freeze(v, seen, path + '/' + str(i)) for i, v in enumerate(value)]
        if isinstance(value, dict):
            return [[self._freeze(k, seen, path + '/key'), self._freeze(v, seen, path + '/' + str(i))] for i, (k, v) in enumerate(sorted(value.items(), key=lambda item: str(item[0])))]
        if isinstance(value, self.pygame.sprite.AbstractGroup):
            return self._freeze(value.sprites(), seen, path)
        module = type(value).__module__
        if not hasattr(value, '__dict__') or not (module.startswith(('game.', 'classes.', 'entities.', 'traits.', 'gameplay.', 'rendering.'))):
            return {'resource_type': type(value).__name__}
        if id(value) in seen:
            return {'native_reference': seen[id(value)]}
        seen[id(value)] = path
        excluded = {'_dead_since', '_cached_3d_model', 'loop', 'screen', 'sound', 'font', 'score_font', 'neon_renderer', 'spriteCollection', 'image', 'src_image', 'normal', 'frames', 'pauseObj', 'input', 'collision', 'EntityCollider', '_Sprite__g', 'camera'}
        fields = {k: self._freeze(v, seen, path + '/' + k) for k, v in sorted(vars(value).items()) if k not in excluded and not callable(v)}
        return {'native_type': module + '.' + type(value).__name__, 'fields': fields}

    def fingerprint(self):
        g = self.env
        if self.GAME == 'race':
            state = {'car': self._freeze(g.car), 'pads': self._freeze(g.pad_group), 'trophy': self._freeze(g.trophy), 'trophy_count': len(g.trophy_group), 'win': g.win_condition, 'origin_distance': g.origin_distance}
        elif self.GAME == 'flappybird':
            names = ('bird_rect', 'bird_movement', 'bird_index', 'bird_flip_count', 'create_pipe_count', 'floor_x_pos', 'pipe_list')
            state = {name: self._freeze(getattr(g, name)) for name in names}
        elif self.GAME == 'pong':
            state = {name: self._freeze(getattr(g, name)) for name in ('ball', 'ball_dx', 'ball_dy', 'paddleA', 'paddleB', 'scoreA', 'scoreB')}
        elif self.GAME == 'supermario':
            state = {'mario': self._freeze(g.mario), 'camera': self._freeze(g.mario.camera), 'dashboard': self._freeze(g.dashboard), 'level': self._freeze(g.level)}
        else:
            m = g.current_mode
            state = {'player': self._freeze(m.player), 'level': self._freeze(m.current_level), 'camera': self._freeze(m.camera), 'rotation': m.current_rotation}
        return _digest({'game': self.GAME, 'native_state': state, 'score': g.score, 'over': g.over,
                        'frame_ledger_count': len(g.game_frames), 'native_step_calls': self.native_step_calls,
                        'native_frames_advanced': self.native_frames_advanced, 'decisions': self.decisions,
                        'terminal_cause': self.terminal_cause, 'random_state': random.getstate(),
                        'numpy_state': self._freeze(self.np.random.get_state())})

    def frame(self):
        return self._frame.copy()

    def close(self):
        if not self._closed:
            self.pygame.quit()
            os.chdir(self._previous_cwd)
            self._temporary.cleanup()
            self._closed = True
