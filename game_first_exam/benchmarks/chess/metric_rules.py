"""Validate the sealed Chess outcome and its half-move record."""
import hashlib
import json
import os
from pathlib import Path
import re

import chess

from config_schema import HASH
from opponent import choose

WHITE, BLACK = 'player_0', 'player_1'
ACTION_COUNT = 4672
ACTION_ID = re.compile(r'0|[1-9][0-9]{0,3}')
UCI_MOVE = re.compile(r'[a-h][1-8][a-h][1-8][qrbn]?')
REWARDS = {'win': [1, -1], 'loss': [-1, 1], 'draw': [0, 0],
           'illegal_action': [-1, 0], 'unfinished': [0, 0]}
POINTS = {'win': 100, 'draw': 50, 'loss': 0, 'illegal_action': 0, 'unfinished': 0}
RESULTS = {'win': '1-0', 'loss': '0-1', 'draw': '1/2-1/2',
           'illegal_action': '*', 'unfinished': '*'}
DRAW_REASONS = {'stalemate', 'insufficient_material', 'fifty_moves', 'threefold_repetition',
                'seventyfive_moves', 'fivefold_repetition'}


def valid_action_id(value):
    return isinstance(value, str) and ACTION_ID.fullmatch(value) is not None and int(value) < ACTION_COUNT


def valid_rewards(actual, expected):
    return (isinstance(actual, list) and len(actual) == 2
            and all(type(value) in (int, float) for value in actual) and actual == expected)


def validate_metrics(final, instance):
    m = final['metrics']
    outcome = m['outcome']
    if outcome not in POINTS:
        raise ValueError('unknown Chess outcome')
    illegal = int(outcome == 'illegal_action')
    if (final['terminated'], final['truncated']) != (outcome != 'unfinished', bool(illegal)):
        raise ValueError('Chess outcome disagrees with native flags')
    if m['native_result'] != RESULTS[outcome] or not valid_rewards(m['native_rewards'], REWARDS[outcome]):
        raise ValueError('Chess outcome disagrees with native result or rewards')
    if (type(m['native_return']) not in (int, float)
            or final['return'] != REWARDS[outcome][0] or m['native_return'] != final['return']):
        raise ValueError('Chess return disagrees with native rewards')
    if (outcome == 'draw' and m['draw_reason'] not in DRAW_REASONS
            or outcome != 'draw' and m['draw_reason'] is not None):
        raise ValueError('invalid Chess draw reason')
    if type(m['match_points']) is not int or m['match_points'] != POINTS[outcome]:
        raise ValueError('inconsistent Chess points')
    if type(m['success']) is not int or m['success'] != int(outcome == 'win') or final['success'] != bool(m['success']):
        raise ValueError('inconsistent Chess success')

    count_fields = ('agent_decisions', 'agent_legal_plies', 'opponent_plies', 'total_board_plies',
                    'native_illegal_actions', 'setup_plies')
    if any(type(m[field]) is not int or m[field] < 0 for field in count_fields):
        raise ValueError('invalid Chess action counts')
    white, black = m['agent_legal_plies'], m['opponent_plies']
    if (m['agent_decisions'] != final['steps'] or m['setup_plies'] != 0
            or m['native_illegal_actions'] != illegal or white + illegal != final['steps']
            or white + black != m['total_board_plies'] or white - black not in (0, 1)
            or (outcome in {'loss', 'unfinished', 'illegal_action'} and white != black)
            or (outcome == 'win' and white != black + 1)):
        raise ValueError('inconsistent Chess action accounting')
    if not isinstance(m['final_fen'], str) or len(m['final_fen'].split()) != 6:
        raise ValueError('missing Chess final FEN')
    if not HASH.fullmatch(m['trace_sha256']):
        raise ValueError('invalid Chess trace digest')
    trace_path = os.environ.get('CHESS_VERIFY_TRACE')
    if trace_path:
        validate_trace(Path(trace_path).read_bytes(), final, instance)


def validate_trace(data, final, instance):
    """Replay the native game's legal moves and verify its outcome."""
    m = final['metrics']
    if hashlib.sha256(data).hexdigest() != m['trace_sha256']:
        raise ValueError('Chess trace digest mismatch')
    events = [json.loads(line) for line in data.splitlines()]
    if len(events) != m['total_board_plies'] + m['native_illegal_actions']:
        raise ValueError('Chess trace length mismatch')
    history = []
    board = chess.Board()
    for index, row in enumerate(events):
        actor = WHITE if index % 2 == 0 else BLACK
        last = index == len(events) - 1
        illegal = last and m['outcome'] == 'illegal_action'
        native_end = last and final['terminated']
        if not isinstance(row, dict):
            raise ValueError('Chess trace entry must be an object')
        if (row['actor'] != actor or row['decision'] != index // 2 + 1 or row['fen_before'] != board.fen()
                or type(row['decision']) is not int or type(row['ply']) is not int
                or row['ply'] != index + 1 - int(illegal)
                or row['terminated'] is not native_end or row['truncated'] is not illegal
                or not valid_rewards(row['rewards'], m['native_rewards'] if last else [0, 0])):
            raise ValueError('Chess trace has inconsistent turn or terminal state')
        legal, action = row['legal_moves'], row['action_id']
        if (not valid_action_id(action) or not isinstance(legal, dict) or not legal
                or any(not valid_action_id(key) or not isinstance(move, str) or not UCI_MOVE.fullmatch(move)
                       for key, move in legal.items())
                or len(set(legal.values())) != len(legal)):
            raise ValueError('Chess trace has an invalid action ID or legal move map')
        if (action in legal) == illegal or row['uci'] != legal.get(action):
            raise ValueError('Chess trace action disagrees with the reported legal mask')
        if set(legal.values()) != {move.uci() for move in board.legal_moves}:
            raise ValueError('Chess trace legal map disagrees with replay')
        if actor == BLACK and action != choose(legal, instance['opponent_seed'], history):
            raise ValueError('Chess trace action disagrees with the frozen opponent')
        if not illegal:
            board.push_uci(row['uci'])
            history.append(row['uci'])
        if row['fen_after'] != board.fen():
            raise ValueError('Chess trace board disagrees with replay')
        # PettingZoo ends on claimable draws as well as checkmate and stalemate.
        outcome = board.outcome(claim_draw=True)
        if (outcome is not None) != (native_end and not illegal):
            raise ValueError('Chess trace termination disagrees with replay')
    if board.fen() != m['final_fen']:
        raise ValueError('Chess trace final FEN mismatch')
    outcome = board.outcome(claim_draw=True)
    if outcome is not None:
        draw_reason = outcome.termination.name.lower() if outcome.winner is None else None
        if outcome.result() != m['native_result'] or draw_reason != m['draw_reason']:
            raise ValueError('Chess trace result disagrees with replay')
