"""Validate native Baba win/loss and step-dependent reward without replaying the engine."""
import math


def validate_metrics(final, instance):
    m = final['metrics']
    for key in ('success', 'lost'):
        if type(m[key]) is not int or m[key] not in (0, 1):
            raise ValueError('invalid native outcome')
    if m['success'] and m['lost']:
        raise ValueError('contradictory native outcome')
    if final['success'] != bool(m['success']):
        raise ValueError('inconsistent success')
    if type(m['native_steps']) is not int or m['native_steps'] != final['steps']:
        raise ValueError('inconsistent native steps')
    if m['native_max_steps'] != instance['native_max_steps']:
        raise ValueError('inconsistent native budget')
    native_end = bool(m['success'] or m['lost'])
    if final['terminated'] != native_end or final['truncated'] != (final['steps'] >= instance['native_max_steps']):
        raise ValueError('inconsistent native flags')
    expected = 1 - .9 * final['steps'] / instance['native_max_steps'] if m['success'] else -float(m['lost'])
    if not math.isclose(m['native_return'], expected) or not math.isclose(final['return'], expected):
        raise ValueError('inconsistent native reward')
