"""One white client decision and at most one black AEC response."""
import copy
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path

import numpy as np
from pettingzoo import make
from pettingzoo.classic.chess import chess_utils

from contracts import Capabilities, Transition
from encoding import state_hash
from metric_rules import ACTION_COUNT, BLACK, POINTS, WHITE
from opponent import choose


class Adapter:
    def __init__(self, instance, assets=None):
        for package, expected in instance['engine_versions'].items():
            if version(package) != expected:
                raise ValueError(f'Chess dependency version mismatch: {package}')
        self.instance = instance
        self.env = make('aec', instance['env_id'], render_mode='rgb_array', screen_height=384)
        try:
            self.env.reset(seed=instance['seed'])
            self.board = self.env.unwrapped.board
            self.history = []
            self.decisions = 0
            self.outcome = 'unfinished'
            self.result = '*'
            self.draw_reason = None
            self.rewards = [0, 0]
            self.terminated = self.truncated = False
            self.trace_digest = hashlib.sha256()
            trace = os.environ.get('CHESS_TRACE_PATH')
            self.trace_path = Path(trace) if trace else None
            if self.trace_path is not None:
                self.trace_path.parent.mkdir(parents=True, exist_ok=True)
                with self.trace_path.open('xb'):
                    pass
            self.refresh_observation([])
        except Exception:
            self.env.close()
            raise

    def spec(self):
        return {
            'adapter_version': '1.0.0',
            'capabilities': Capabilities(False, 'enum', native_truncation=True).to_dict(),
            'action_schema': {'type': 'string', 'enum': [str(i) for i in range(ACTION_COUNT)],
                              'max_length': 4},
            'goal': 'Win the native game as white.',
        }

    def legal_map(self, actor, mask):
        return {str(index): chess_utils.action_to_move(self.board, int(index), int(actor == BLACK)).uci()
                for index in np.flatnonzero(mask)}

    def refresh_observation(self, moves):
        native = self.env.observe(WHITE)
        self.white_legal = {} if self.terminated or self.truncated else self.legal_map(WHITE, native['action_mask'])
        self.public = {
            'native_observation': native['observation'].tolist(),
            'action_mask': native['action_mask'].tolist(),
            'controlled_agent': WHITE,
            'side_to_move': 'white' if self.board.turn else 'black',
            'board_fen': self.board.fen(),
            'board_ascii': str(self.board),
            'legal_moves': self.white_legal,
            'last_round_moves': moves,
            'move_history_uci': list(self.history),
            'outcome': self.outcome,
        }

    def observe(self):
        return copy.deepcopy(self.public)

    def native_step(self, actor, action, legal):
        if self.env.agent_selection != actor:
            raise RuntimeError('unexpected native Chess actor')
        before = self.board.fen()
        uci = legal.get(action)
        self.env.step(int(action))
        self.rewards = [self.env.rewards[player] for player in (WHITE, BLACK)]
        self.terminated = all(self.env.terminations.values())
        self.truncated = all(self.env.truncations.values())
        if uci is not None:
            self.history.append(uci)
        if self.terminated:
            if uci is None:
                self.outcome = 'illegal_action'
            else:
                outcome = self.board.outcome(claim_draw=True)
                self.result = outcome.result()
                self.outcome = {'1-0': 'win', '0-1': 'loss', '1/2-1/2': 'draw'}[self.result]
                if self.outcome == 'draw':
                    self.draw_reason = outcome.termination.name.lower()
        row = {'actor': actor, 'action_id': action, 'uci': uci, 'decision': self.decisions,
               'ply': self.board.ply(), 'fen_before': before, 'fen_after': self.board.fen(),
               'rewards': self.rewards, 'terminated': self.terminated, 'truncated': self.truncated,
               'legal_moves': legal}
        data = (json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n').encode()
        if self.trace_path is not None:
            with self.trace_path.open('ab') as stream:
                stream.write(data)
        self.trace_digest.update(data)
        return {'actor': actor, 'action_id': action, 'uci': uci}

    def step(self, action):
        if self.terminated or self.truncated:
            raise ValueError('episode closed')
        self.decisions += 1
        moves = [self.native_step(WHITE, action, self.white_legal)]
        reward = self.rewards[0]
        if not (self.terminated or self.truncated):
            legal = self.legal_map(BLACK, self.env.observe(BLACK)['action_mask'])
            response = choose(legal, self.instance['opponent_seed'], self.history)
            if response not in legal:
                raise RuntimeError('fixed opponent returned an illegal Chess action')
            moves.append(self.native_step(BLACK, response, legal))
            reward += self.rewards[0]
        self.refresh_observation(moves)
        return Transition(float(reward), self.terminated, self.truncated)

    def success(self):
        return self.outcome == 'win'

    def metrics(self):
        plies = len(self.history)
        return {'outcome': self.outcome, 'match_points': POINTS[self.outcome],
                'success': int(self.success()), 'native_result': self.result,
                'native_return': self.rewards[0], 'native_rewards': self.rewards.copy(),
                'draw_reason': self.draw_reason, 'agent_decisions': self.decisions,
                'agent_legal_plies': (plies + 1) // 2, 'opponent_plies': plies // 2,
                'total_board_plies': plies, 'setup_plies': 0,
                'native_illegal_actions': int(self.outcome == 'illegal_action'),
                'final_fen': self.board.fen(), 'trace_sha256': self.trace_digest.hexdigest()}

    def fingerprint(self):
        return state_hash({'metrics': self.metrics(), 'actor': self.env.agent_selection,
                           'flags': [self.env.terminations, self.env.truncations],
                           'board_history': self.env.unwrapped.board_history,
                           'seed': self.instance['seed'], 'opponent_seed': self.instance['opponent_seed'],
                           'opponent_policy': self.instance['opponent_policy']})

    def frame(self):
        return self.env.render()

    def close(self):
        self.env.close()
