"""Native FightingICE match behind the shared synchronous game contract."""
import copy
import importlib.metadata
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

from bridge import Session
from contracts import Capabilities, Transition
from encoding import state_hash
from install_native import verify
from pyftg import Key
from pyftg.models.enums.int_action import IntAction
from pyftg.models.enums.int_state import IntState

KEYS = 'ABCDLRU'
ACTIONS = ['noop'] + [''.join(key for bit, key in enumerate(KEYS) if mask & (1 << bit))
                      for mask in range(1, 128)]


class Adapter:
    def __init__(self, instance, assets=None):
        if importlib.metadata.version('pyftg') != instance['engine_versions']['pyftg']:
            raise ValueError('pyftg version mismatch')
        self.instance = copy.deepcopy(instance)
        self.player = instance['player']
        self.steps, self.rounds, self.done = 0, [], False
        self.data, self.audit, self.is_control = None, None, False
        self.session = self.process = None
        self.workspace = tempfile.TemporaryDirectory(prefix='fightingice-')
        self.log = None
        try:
            native = Path(os.environ.get('FIGHTINGICE_HOME', '/opt/fightingice'))
            verify(native)
            shutil.copytree(native, self.workspace.name, dirs_exist_ok=True)
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            self.log = open(Path(self.workspace.name) / 'engine.log', 'wb')
            self.process = subprocess.Popen([
                'java', '-Xmx512m', '-XX:ActiveProcessorCount=1', '-cp',
                'FightingICE.jar:lib/*:lib/grpc/*:lib/lwjgl/*', 'Main',
                '--lightweight-mode', '--input-sync', '--limithp', '400', '400',
                '--pyftg-mode', '--port', str(port)], cwd=self.workspace.name,
                env={**os.environ, 'SERVER_HOST': '127.0.0.1'}, stdout=self.log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 15
            while True:
                if self.process.poll() is not None:
                    raise RuntimeError('FightingICE exited during startup')
                # An empty TCP probe can kill the native accept thread. Wait for
                # its own ready marker without sending a partial player packet.
                if 'Waiting to launch a game' in (Path(self.workspace.name) / 'engine.log').read_text():
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError('FightingICE socket did not become ready')
                time.sleep(.05)
            self.session = Session(port, self.player)
            self._advance()
        except Exception as exc:
            detail = (Path(self.workspace.name) / 'engine.log').read_text() if self.log else ''
            self.close()
            raise RuntimeError(f'{exc}\n{detail[-4000:]}') from exc

    def _advance(self):
        while True:
            event = self.session.next()
            if event[0] == 'frame':
                _, self.data, self.is_control, self.audit = event
                return
            if event[0] == 'round':
                self.rounds.append(event[1])
            elif event[0] == 'end':
                self.done = True
                return
            else:
                raise RuntimeError('unknown native callback')

    def spec(self):
        return {'adapter_version': '1.0.0',
                'capabilities': Capabilities(images=False, action_mode='enum').to_dict(),
                'action_schema': {'type': 'string', 'enum': ACTIONS},
                'observation': 'native delayed FrameData; native is_control; zero-based player index',
                'keys': {'A': 'attack A', 'B': 'attack B', 'C': 'attack C', 'D': 'down',
                         'L': 'left', 'R': 'right', 'U': 'up', 'noop': 'release all keys'},
                'frames_per_action': 1, 'native_fps': 60,
                'native_action_ids': {name: int(value) for name, value in IntAction.__members__.items()},
                'native_state_ids': {name: int(value) for name, value in IntState.__members__.items()},
                'game_data': copy.deepcopy(self.session.game_data)}

    def observe(self):
        return {'player': self.player, 'frame_data': copy.deepcopy(self.data), 'is_control': self.is_control}

    def step(self, action):
        if action not in ACTIONS or self.done:
            raise ValueError('invalid native key or closed match')
        key = Key()
        for name in (() if action == 'noop' else action):
            setattr(key, name, True)
        self.session.actions.put(key)
        self._advance()
        self.steps += 1
        return Transition(0.0, terminated=self.done)

    def metrics(self):
        wins = sum(r['remaining_hps'][self.player] > r['remaining_hps'][1-self.player] for r in self.rounds)
        losses = sum(r['remaining_hps'][self.player] < r['remaining_hps'][1-self.player] for r in self.rounds)
        return {'rounds': copy.deepcopy(self.rounds), 'wins': wins, 'losses': losses,
                'draws': len(self.rounds)-wins-losses, 'completed_rounds': len(self.rounds),
                'round_win_score': 100*wins/3, 'native_steps': self.steps}

    def success(self):
        metrics = self.metrics()
        return self.done and metrics['wins'] > metrics['losses']

    def fingerprint(self):
        identifiers = {}

        def canonical(value):
            if isinstance(value, dict):
                result = {}
                for key, item in value.items():
                    if key == 'identifier' and item:
                        item = identifiers.setdefault(item, len(identifiers))
                    result[key] = canonical(item)
                return result
            if isinstance(value, list):
                return [canonical(item) for item in value]
            return value

        # Native UUIDs identify attacks but have random bytes. Keep within-state
        # identity relationships in the audit hash without changing observations.
        return state_hash(canonical({'frame': self.audit, 'delayed_frame': self.data, 'rounds': self.rounds,
                                     'steps': self.steps, 'done': self.done, 'player': self.player}))

    def frame(self):
        import numpy as np
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (640, 200), '#202020')
        draw = ImageDraw.Draw(image)
        draw.text((12, 12), 'FightingICE native-state transcript (not game pixels)', fill='white')
        draw.text((12, 32), f'Controlled P{self.player+1}; input {self.steps}; rounds {len(self.rounds)}/3', fill='white')
        frame = self.audit or self.data or {}
        for index, character in enumerate(frame.get('character_data', [])):
            if character:
                draw.text((12, 60+index*55), f'P{index+1}: HP {character["hp"]}; {character["action"]}', fill='white')
        return np.asarray(image)

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait(timeout=5)
        try:
            if self.session is not None:
                self.session.close()
        finally:
            if self.log is not None:
                self.log.close()
            self.workspace.cleanup()
