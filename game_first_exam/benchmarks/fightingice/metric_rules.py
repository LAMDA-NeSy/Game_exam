"""Validate native rounds and fixed-denominator match scores in the verifier."""
import math


def validate_metrics(final, instance):
    metrics = final['metrics']
    required = {'rounds', 'wins', 'losses', 'draws', 'completed_rounds', 'round_win_score', 'native_steps'}
    if not isinstance(metrics, dict) or set(metrics) != required:
        raise ValueError('unexpected FightingICE metrics')
    rounds = metrics['rounds']
    if not isinstance(rounds, list) or len(rounds) > instance['rounds']:
        raise ValueError('invalid native round count')
    wins = losses = 0
    for index, result in enumerate(rounds, 1):
        if not isinstance(result, dict) or set(result) != {'current_round', 'remaining_hps', 'elapsed_frame'}:
            raise ValueError('malformed native round result')
        if type(result['current_round']) is not int or result['current_round'] != index:
            raise ValueError('native rounds must be complete and consecutive')
        hp, elapsed = result['remaining_hps'], result['elapsed_frame']
        if not isinstance(hp, list) or len(hp) != 2 or any(type(x) is not int or not -400 <= x <= 400 for x in hp):
            raise ValueError('invalid native remaining HP')
        if type(elapsed) is not int or not 1 <= elapsed <= instance['round_frames']:
            raise ValueError('invalid native elapsed frames')
        if min(hp) > 0 and elapsed != instance['round_frames']:
            raise ValueError('round ended without KO or the native frame limit')
        wins += hp[instance['player']] > hp[1-instance['player']]
        losses += hp[instance['player']] < hp[1-instance['player']]
    expected = {'wins': wins, 'losses': losses, 'draws': len(rounds)-wins-losses,
                'completed_rounds': len(rounds), 'native_steps': final['steps']}
    if any(type(metrics[key]) is not int or metrics[key] != value for key, value in expected.items()):
        raise ValueError('inconsistent native match counters')
    score = metrics['round_win_score']
    if type(score) not in (int, float) or not math.isfinite(score) or not math.isclose(score, 100*wins/3, abs_tol=1e-9):
        raise ValueError('inconsistent fixed-denominator score')
    completed = len(rounds) == instance['rounds']
    if final['terminated'] != completed or final['truncated'] or final['return'] != 0:
        raise ValueError('inconsistent native match ending or invented scalar reward')
    if final['success'] != (completed and wins > losses):
        raise ValueError('inconsistent match success')
    elapsed = sum(result['elapsed_frame'] for result in rounds)
    if (final['steps'] < elapsed or final['steps'] > instance['rounds']*instance['round_frames']
            or (completed and final['steps'] != elapsed)
            or (not completed and final['steps'] >= elapsed + instance['round_frames'])):
        raise ValueError('native frames disagree with action count')
