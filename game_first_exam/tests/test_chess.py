"""Chess adapter, public service and independent grading checks."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / path) for path in ('scripts', 'game_first_exam/runtime',
                                           'game_first_exam/benchmarks/chess')]

from adapter import Adapter
from config_schema import validate_instance
from game_schemas import load_schema
from grade import grade
from metric_rules import validate_metrics
from server import Game, InvalidAction

INSTANCE = ROOT / 'game_first_exam/tasks/chess/chess-match-i01-standard/tests/instance.json'


class ChessIntegrationTests(unittest.TestCase):
    def setUp(self):
        load_schema('chess')
        self.instance = json.loads(INSTANCE.read_text())
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.output = Path(temp.name)
        self.trace = self.output / 'chess_plies.jsonl'

    def open_game(self):
        with patch.dict(os.environ, {'CHESS_TRACE_PATH': str(self.trace)}):
            game = Game.open(Adapter, self.instance, None, self.output)
        self.addCleanup(game.close)
        self.assertIsNone(game.final)
        return game

    def play(self, game, uci):
        action = next(key for key, move in game.observe()['observation']['legal_moves'].items() if move == uci)
        return game.submit({'action': action, 'expected_step': game.steps, 'request_id': str(game.steps)})

    def score(self, game, outcome, points, trace=True):
        self.assertEqual(game.final['metrics']['outcome'], outcome)
        with patch.dict(os.environ, {'CHESS_VERIFY_TRACE': str(self.trace) if trace else ''}):
            result = grade(game.final, self.instance, validate_metrics)
        self.assertEqual(result['primary_score'], points)
        self.assertEqual(result['success'], float(outcome == 'win'))

    def test_round_retry_determinism_and_public_budget(self):
        self.instance['max_steps'] = 1
        game = self.open_game()
        initial = game.adapter.fingerprint()
        public = game.adapter.observe()
        public['legal_moves'].clear()
        game.adapter.frame()
        self.assertEqual(game.adapter.fingerprint(), initial)
        self.assertEqual(len(game.observe()['observation']['legal_moves']), 20)
        with self.assertRaises(InvalidAction):
            game.submit({'action': '4672', 'expected_step': 0, 'request_id': 'rejected'})
        self.assertEqual(game.steps, 0)
        self.assertEqual(self.trace.read_bytes(), b'')
        action = next(iter(game.observe()['observation']['legal_moves']))
        request = {'action': action, 'expected_step': 0, 'request_id': 'retry'}
        result = game.submit(request)
        self.assertEqual(game.submit(request), result)
        self.assertEqual(result['observation']['side_to_move'], 'white')
        self.assertEqual(game.final['reason'], 'step_limit')
        self.score(game, 'unfinished', 0)
        other = Adapter(self.instance)
        self.addCleanup(other.close)
        self.assertEqual(other.fingerprint(), initial)
        other.step(action)
        self.assertEqual(other.fingerprint(), game.adapter.fingerprint())
        self.assertEqual(other.metrics()['total_board_plies'], 2)
        original = self.trace.read_bytes()
        self.trace.write_bytes(original + b'\n')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            self.score(game, 'unfinished', 0)

    def test_native_illegal_and_verifier_mismatch(self):
        game = self.open_game()
        response = game.submit({'action': '0', 'expected_step': 0, 'request_id': 'illegal'})
        self.assertTrue(response['done'])
        self.assertEqual(response['observation']['legal_moves'], {})
        self.assertEqual(game.final['metrics']['total_board_plies'], 0)
        self.score(game, 'illegal_action', 0)
        final = copy.deepcopy(game.final)
        final['metrics']['match_points'] = 50
        with self.assertRaisesRegex(ValueError, 'points'):
            grade(final, self.instance, validate_metrics)

    def test_verifier_rejects_malformed_evidence_even_with_matching_digest(self):
        game = self.open_game()
        self.play(game, 'e2e4')
        game.finalize('agent_finished')
        events = [json.loads(line) for line in self.trace.read_bytes().splitlines()]
        for update in ({'terminated': 0}, {'decision': True}, {'rewards': [False, 0]},
                       {'action_id': '04672'}, {'legal_moves': {'1': 'bad'}}):
            with self.subTest(update=update):
                first = {**events[0], **update}
                payload = b''.join((json.dumps(row) + '\n').encode() for row in [first, *events[1:]])
                self.trace.write_bytes(payload)
                invalid = copy.deepcopy(game.final)
                invalid['metrics']['trace_sha256'] = hashlib.sha256(payload).hexdigest()
                with patch.dict(os.environ, {'CHESS_VERIFY_TRACE': str(self.trace)}), self.assertRaises(ValueError):
                    grade(invalid, self.instance, validate_metrics)
        invalid = copy.deepcopy(game.final)
        invalid['metrics']['native_return'] = False
        with self.assertRaisesRegex(ValueError, 'return'):
            grade(invalid, self.instance, validate_metrics)

    def scripted(self, responses):
        """Use real AEC moves while forcing a terminal test fixture for Black."""
        remaining = iter(responses.split())

        def policy(legal, seed, history):
            response = next(remaining)
            return next(key for key, move in legal.items() if move == response)

        return patch('adapter.choose', side_effect=policy)

    def test_native_loss(self):
        game = self.open_game()
        with self.scripted('e7e5 d8h4'):
            self.play(game, 'f2f3')
            self.assertTrue(self.play(game, 'g2g4')['done'])
        self.score(game, 'loss', 0, trace=False)
        self.assertEqual(game.final['metrics']['total_board_plies'], 4)

    def test_native_win_on_last_decision(self):
        self.instance['max_steps'] = 4
        game = self.open_game()
        with self.scripted('e7e5 b8c6 g8f6') as black:
            for uci in ('e2e4', 'f1c4', 'd1h5', 'h5f7'):
                result = self.play(game, uci)
        self.assertEqual(black.call_count, 3)
        self.assertTrue(result['done'])
        self.assertTrue(game.final['budget_exhausted'])
        self.assertEqual(game.final['reason'], 'native_terminated')
        self.score(game, 'win', 100, trace=False)

    def test_native_draw(self):
        game = self.open_game()
        with self.scripted('g8f6 f6g8 g8f6'):
            for uci in ('g1f3', 'f3g1', 'g1f3', 'f3g1'):
                result = self.play(game, uci)
        self.assertTrue(result['done'])
        self.assertEqual(game.final['metrics']['draw_reason'], 'threefold_repetition')
        self.score(game, 'draw', 50, trace=False)

    def test_zero_decisions_are_unfinished(self):
        game = self.open_game()
        game.finalize('agent_finished')
        self.score(game, 'unfinished', 0)

    def test_illegal_opponent_invalidates_environment(self):
        game = self.open_game()
        with patch('adapter.choose', return_value='invalid'), self.assertRaisesRegex(RuntimeError, 'environment execution'):
            self.play(game, 'e2e4')
        result = grade(game.final, self.instance, validate_metrics)
        self.assertFalse(result['result_valid'])
        self.assertIsNone(result['primary_score'])

    def test_configuration_fails_closed(self):
        validate_instance(self.instance)
        for field, value in (('opponent_policy', 'unknown'), ('controlled_agent', 'player_1'),
                             ('observation_profile', 'native'), ('opponent_seed', True), ('x', 1)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_instance({**self.instance, field: value})
        metrics = {**self.instance['metric_spec'], 'reducer': 'unknown'}
        with self.assertRaises(ValueError):
            validate_instance({**self.instance, 'metric_spec': metrics})


if __name__ == '__main__':
    unittest.main()
