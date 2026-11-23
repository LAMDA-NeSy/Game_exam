"""Validate native 2048 score, tile and move-count relationships."""
import math


def validate_metrics(final, instance):
    metrics = final['metrics']
    expected = {'target_reached', 'native_score', 'max_tile', 'valid_moves',
                'invalid_moves', 'native_return'}
    if set(metrics) != expected:
        raise ValueError('wrong 2048 metric fields')
    for key in ('target_reached', 'native_score', 'max_tile',
                'valid_moves', 'invalid_moves'):
        if type(metrics[key]) is not int:
            raise ValueError('2048 integer metric has wrong type: ' + key)
    score, maximum = metrics['native_score'], metrics['max_tile']
    valid, invalid = metrics['valid_moves'], metrics['invalid_moves']
    if score < 0 or score % 4 or valid < 0 or invalid < 0:
        raise ValueError('invalid 2048 score or move count')
    if (maximum < 2 or maximum > 2 ** (instance['native_max_power'] - 1)
            or maximum & (maximum - 1)):
        raise ValueError('invalid 2048 maximum tile')
    if valid + invalid != final['steps']:
        raise ValueError('2048 move counts disagree with accepted steps')
    if not isinstance(metrics['native_return'], (int, float)) or isinstance(
            metrics['native_return'], bool) or not math.isfinite(metrics['native_return']):
        raise ValueError('invalid 2048 native return')
    if metrics['native_return'] != score or final['return'] != score:
        raise ValueError('2048 score disagrees with native return')
    reached = int(maximum >= 2 ** instance['target_power'])
    if metrics['target_reached'] != reached:
        raise ValueError('2048 target flag disagrees with maximum tile')
    if final['success'] != (bool(reached) and not final['sim_error']):
        raise ValueError('2048 success disagrees with target tile')
    if final['steps'] == 0 and (score or valid or invalid or maximum > 4):
        raise ValueError('2048 progress without an action')
