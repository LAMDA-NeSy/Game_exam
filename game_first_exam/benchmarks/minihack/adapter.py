"""MiniHack tasks with native observations, actions and rewards."""
import importlib.metadata
import json
import os
import time
from pathlib import Path

import gymnasium as gym
import minihack  # noqa: F401 - registers the upstream environments
import numpy as np
from contracts import Capabilities, Transition
from encoding import state_hash
from PIL import Image, ImageDraw


CROP_FIELDS = ('glyphs_crop', 'chars_crop', 'colors_crop', 'specials_crop', 'blstats', 'message')
QUEST_PROFILE = 'player-crop-inventory-9x9-v1'
OBSERVATION_FIELDS = {
    'native-observation-v1': ('glyphs', 'chars', 'colors', 'specials', *CROP_FIELDS),
    'player-crop-9x9-v1': CROP_FIELDS,
    QUEST_PROFILE: (*CROP_FIELDS, 'inv_letters', 'inv_strs'),
}


def make_native_env(env_id, assets):
    if not env_id.startswith('MiniHack-Boxoban-'):
        return gym.make(env_id)

    from minihack.envs import boxohack

    # Native MiniHack reads the dataset during construction. Each frozen task
    # supplies one upstream level so the native random choice is reproducible.
    dataset = Path(assets) / 'boxoban'
    original = boxohack.LEVELS_PATH
    try:
        boxohack.LEVELS_PATH = dataset
        # Gymnasium's checker always forwards seed= to reset, which BoxoHack
        # does not accept in the pinned version.
        return gym.make(env_id, disable_env_checker=True)
    finally:
        boxohack.LEVELS_PATH = original


class Adapter:
    def __init__(self, instance, assets=None):
        self.instance = instance
        self.observation_fields = OBSERVATION_FIELDS[instance['observation_profile']]
        clock = instance['native_clock']
        if (os.environ.get('FAKETIME') != '@2026-11-13 12:00:00'
                or os.environ.get('FAKETIME_DONT_FAKE_MONOTONIC') != '1'
                or os.environ.get('TZ') != 'UTC'
                or time.strftime('%Y-%m-%d', time.gmtime()) != clock['start_utc'][:10]):
            raise ValueError('native calendar clock mismatch; start with the pinned simulator clock')
        for name, version in instance['engine_versions'].items():
            if importlib.metadata.version(name) != version:
                raise ValueError('MiniHack dependency version mismatch: ' + name)
        source = json.loads(importlib.metadata.distribution('minihack').read_text('direct_url.json'))
        if source['archive_info']['hashes']['sha256'] != instance['engine_archive_sha256']:
            raise ValueError('MiniHack source archive mismatch')
        # No task, observation, reward, character or time-limit overrides.
        self.boxoban = instance['env_id'].startswith('MiniHack-Boxoban-')
        self.quest = instance['observation_profile'] == QUEST_PROFILE
        self.env = make_native_env(instance['env_id'], assets)
        native = self.env.unwrapped
        if native._max_episode_steps != instance['native_max_steps']:
            self.env.close()
            raise ValueError('native episode limit mismatch')
        # reset(seed=...) only seeds Gymnasium in this NLE version. Use NLE's API too.
        native.seed(instance['seed'], instance['seed'], reseed=False)
        if self.boxoban:
            # NLE checks terminal status during reset, before BoxoHack reads
            # the fountain locations from the new board.
            native._goal_pos_set = frozenset()
            self.obs, self.info = self.env.reset()
        else:
            self.obs, self.info = self.env.reset(seed=instance['seed'])
        self.actions = {}
        for index, action in enumerate(native.actions):
            name = action.name
            if self.quest and name in self.actions:
                # Quest has both lowercase movement and uppercase long movement.
                name = 'RUN_' + name
            self.actions[name] = index
        if len(self.actions) != len(native.actions):
            self.env.close()
            raise ValueError('ambiguous native action names')
        self.total_return = 0.0
        self.ended = False

    def spec(self):
        spec = {'adapter_version': '1.0.0',
                'capabilities': Capabilities(images=False, action_mode='enum', native_truncation=True).to_dict(),
                'action_schema': {'type': 'string', 'enum': list(self.actions)},
                'observation': 'Native MiniHack arrays serialized as JSON lists. Fields are '
                               + ', '.join(self.observation_fields) + '.',
                'action_indices': self.actions,
                'goal': ('Push all four boulders onto the fountains.' if self.boxoban
                         else 'Complete the native task by reaching the down staircase (>).')}
        if self.quest:
            spec['action_keys'] = {name: int(self.env.unwrapped.actions[index])
                                   for name, index in self.actions.items()}
        return spec

    def observe(self):
        return {key: self.obs[key].tolist() for key in self.observation_fields}

    def step(self, action):
        if self.ended:
            raise ValueError('episode closed')
        self.obs, reward, terminated, truncated, self.info = self.env.step(self.actions[action])
        self.total_return += float(reward)
        self.ended = bool(terminated or truncated)
        return Transition(float(reward), bool(terminated), bool(truncated))

    def success(self):
        return self.info['end_status'] == self.env.unwrapped.StepStatus.TASK_SUCCESSFUL

    def metrics(self):
        success = int(self.success())
        return {'success': success, 'completion_score': 100 * success, 'native_return': self.total_return,
                'native_end_status': int(self.info['end_status']),
                'native_steps': self.env.unwrapped._steps,
                'native_max_steps': self.env.unwrapped._max_episode_steps}

    def fingerprint(self):
        native = self.env.unwrapped
        # NLE exposes observations and current seeds, not a complete engine checkpoint.
        # Internal observations are audit-only and are never forwarded to the agent.
        return state_hash({'observations': native.last_observation,
                           'seeds': native.get_seeds(), 'steps': native._steps,
                           'frozen_steps': native._frozen_steps,
                           'end_status': int(self.info['end_status']),
                           'return': self.total_return})

    def frame(self):
        # Terminal transcript for audit video only; not an added agent observation.
        chars = self.obs['chars']
        canvas = Image.new('RGB', (chars.shape[1] * 10 + 4, chars.shape[0] * 14 + 28), 'black')
        draw = ImageDraw.Draw(canvas)
        draw.text((2, 2), 'MiniHack | native terminal transcript', fill='white')
        for y, row in enumerate(chars):
            for x, char in enumerate(row):
                if 32 < char < 127:
                    draw.text((2 + x * 10, 24 + y * 14), chr(int(char)), fill='white')
        return np.asarray(canvas)

    def close(self):
        self.env.close()
