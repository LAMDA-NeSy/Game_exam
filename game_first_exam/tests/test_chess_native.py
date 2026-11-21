"""Behavior probes for the pinned PettingZoo Chess AEC environment."""
import hashlib
from pathlib import Path
import unittest

import chess
import numpy as np
from pettingzoo import make
from pettingzoo.classic.chess import chess_utils


def legal_map(env):
    actor = env.agent_selection
    board = env.unwrapped.board
    mask = env.observe(actor)['action_mask']
    return {chess_utils.action_to_move(board, int(i), int(actor == 'player_1')).uci(): int(i)
            for i in np.flatnonzero(mask)}


def play(env, moves):
    for move in moves.split():
        assert not any(env.terminations.values())
        assert env.step(legal_map(env)[move]) is None


class NativeChessTests(unittest.TestCase):
    def new_env(self, **kwargs):
        env = make('aec', 'classic/chess-v6', **kwargs)
        self.addCleanup(env.close)
        self.assertIsNone(env.reset(seed=123, options={'fen': 'ignored'}))
        return env

    def test_source_and_reset_observation(self):
        source = Path(chess_utils.__file__).parent
        for name, expected in {
            'chess.py': '2b5c6f684951bb1b476213db88fcbebf63ed7acf0c565e288454f3174752726a',
            'chess_utils.py': 'e9a7418ab85bbbb2f5ed5cd766b5afcc7ff07a6ca110842f48465f4ec9717cc1',
        }.items():
            self.assertEqual(hashlib.sha256((source / name).read_bytes()).hexdigest(), expected)
        env = self.new_env(render_mode='rgb_array', screen_height=128)
        self.assertFalse(env.metadata['is_parallelizable'])
        self.assertEqual(env.agent_selection, 'player_0')
        self.assertEqual(env.unwrapped.board.fen(), chess.STARTING_FEN)
        white = env.observe('player_0')
        self.assertEqual(white['observation'].shape, (8, 8, 111))
        self.assertEqual(white['observation'].dtype, np.bool_)
        self.assertFalse(white['observation'][..., 7:].any())
        self.assertEqual(white['action_mask'].shape, (4672,))
        self.assertEqual(white['action_mask'].dtype, np.int8)
        self.assertEqual(white['action_mask'].sum(), 20)
        self.assertFalse(env.observe('player_1')['action_mask'].any())
        white_id = legal_map(env)['e2e4']
        play(env, 'e2e4')
        self.assertEqual(env.agent_selection, 'player_1')
        self.assertEqual(legal_map(env)['e7e5'], white_id)
        white = env.observe('player_0')['observation']
        black = env.observe('player_1')['observation']
        np.testing.assert_array_equal(black[..., 7:13], white[::-1, :, 13:19])
        before = env.unwrapped.board.fen(), env.unwrapped.board_history.copy()
        frame = env.render()
        self.assertEqual(frame.shape, (128, 128, 3))
        self.assertEqual(frame.dtype, np.uint8)
        env.observe('player_1')
        self.assertEqual(env.unwrapped.board.fen(), before[0])
        np.testing.assert_array_equal(env.unwrapped.board_history, before[1])
        print(f'Native initial mask=20, e2e4/e7e5 ID={white_id}, rgb_array={frame.shape}')

    def test_special_moves_and_all_legal_ids(self):
        for moves, expected in (
            ('e2e4 a7a6 e4e5 d7d5', {'e5d6'}),
            ('e2e4 e7e5 g1f3 g8f6 f1c4 f8c5', {'e1g1'}),
            ('a2a4 h7h5 a4a5 h5h4 a5a6 h4h3 a6b7 h3g2',
             {'b7a8' + suffix for suffix in 'qrbn'}),
        ):
            env = self.new_env()
            for move in moves.split():
                lookup = legal_map(env)
                self.assertEqual(set(lookup), {m.uci() for m in env.unwrapped.board.legal_moves})
                env.step(lookup[move])
            self.assertLessEqual(expected, legal_map(env).keys())

    def test_checkmate_draw_illegal_and_dead_steps(self):
        for moves, rewards, truncated in (
            ('f2f3 e7e5 g2g4 d8h4', (-1, 1), False),
            ('g1f3 g8f6 f3g1 f6g8 g1f3 g8f6 f3g1', (0, 0), False),
            ('', (-1, 0), True),
        ):
            env = self.new_env()
            if moves:
                play(env, moves)
            else:
                with self.assertRaises(AssertionError):
                    env.step(4672)
                self.assertFalse(any(env.terminations.values()))
                env.step(0)
                self.assertEqual(env.unwrapped.board.ply(), 0)
                self.assertTrue(env.observe(env.agent_selection)['action_mask'].any())
            self.assertEqual(tuple(env.rewards.values()), rewards)
            self.assertEqual(tuple(env.terminations.values()), (True, True))
            self.assertEqual(tuple(env.truncations.values()), (truncated, truncated))
            print(f'Native ply={env.unwrapped.board.ply()} rewards={env.rewards} truncation={truncated}')
            with self.assertRaises(ValueError):
                env.step(0)
            env.step(None)
            env.step(None)
            self.assertEqual(env.agents, [])

    def test_reproducible(self):
        one, two = self.new_env(), self.new_env()
        for env in (one, two):
            play(env, 'e2e4 c7c5 g1f3 d7d6')
        for key, value in one.observe('player_0').items():
            np.testing.assert_array_equal(value, two.observe('player_0')[key])
        self.assertEqual(one.unwrapped.board.fen(), two.unwrapped.board.fen())


if __name__ == '__main__':
    unittest.main()
