"""Scoring and completeness checks for mixed-game runs."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from run_games import aggregate


def record(benchmark, family, primary, reducer='family_macro'):
    return {'benchmark': benchmark, 'family': family, 'seed': 42, 'digest': 'frozen',
            'metric_spec': {'primary': primary, 'reducer': reducer, 'reducer_version': '1.0.0', 'success_label': 'test'}}


def trial(name, score, success=0, valid=True):
    return {'task': name, 'success': success, 'valid': valid, 'steps': 3,
            'native_metrics': {'score': score, 'achievement_fraction': score,
                               'achievements': {'wood': 1, 'diamond': 0}}}


class Reports(unittest.TestCase):
    def test_native_score_is_preserved_for_valid_binary_failure(self):
        records = {'c1': record('crafter', 'survival', 'achievement_fraction', 'crafter_achievements'),
                   't1': record('textworld', 'cooking', 'score')}
        result = aggregate([trial('c1', .5), trial('t1', .6)], records)
        self.assertTrue(result['complete'])
        self.assertEqual(result['benchmarks']['crafter']['macro_primary_score'], .5)
        self.assertAlmostEqual(result['benchmarks']['crafter']['crafter_score'], 101 ** .5 - 1)
        self.assertEqual(result['benchmarks']['textworld']['macro_primary_score'], .6)
        self.assertNotIn('overall_score', result)

    def test_missing_infrastructure_and_duplicates_cannot_improve_complete_macro(self):
        records = {f't{i}': record('textworld', 'cooking' if i < 2 else 'treasure', 'score') for i in range(3)}
        rows = [trial('t0', 1, 1), trial('t1', 0, valid=False)]
        result = aggregate(rows, records)['benchmarks']['textworld']
        self.assertFalse(result['complete'])
        self.assertIsNone(result['macro_primary_score'])
        self.assertEqual((result['valid'], result['infra_errors'], result['missing']), (1, 1, 1))
        with self.assertRaises(ValueError):
            aggregate([trial('other', 1)], records)
        with self.assertRaises(ValueError):
            aggregate([trial('t0', 1), trial('t0', 0)], records)

    def test_family_macro_weights_families_not_episode_counts(self):
        records = {'a': record('textworld', 'one', 'score'), 'b': record('textworld', 'one', 'score'),
                   'c': record('textworld', 'two', 'score')}
        group = aggregate([trial('a', 1), trial('b', 1), trial('c', 0)], records)['benchmarks']['textworld']
        self.assertAlmostEqual(group['mean_primary_score'], 2 / 3)
        self.assertEqual(group['macro_primary_score'], .5)


if __name__ == '__main__':
    unittest.main()
