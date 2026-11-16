"""Check MiniHack completion scores and native episode evidence."""
import math


def validate_metrics(final, instance):
    metrics = final['metrics']
    status = metrics['native_end_status']
    if type(status) is not int or status not in {-1, 0, 1, 2}:
        raise ValueError('unknown native MiniHack end status')
    if type(metrics['success']) is not int or metrics['success'] != int(status == 2):
        raise ValueError('inconsistent native success')
    if final['success'] != (status == 2):
        raise ValueError('inconsistent success flag')
    if 'completion_score' in metrics or instance['metric_spec']['primary'] == 'completion_score':
        score = metrics.get('completion_score')
        if type(score) is not int or score != 100 * int(status == 2):
            raise ValueError('inconsistent MiniHack completion score')
    if type(metrics['native_steps']) is not int or metrics['native_steps'] != final['steps']:
        raise ValueError('inconsistent native action count')
    if metrics['native_max_steps'] != instance['native_max_steps']:
        raise ValueError('inconsistent native limit')
    if metrics['native_return'] != final['return']:
        raise ValueError('inconsistent native return')
    if status != 0 and not (final['terminated'] or final['truncated']):
        raise ValueError('native end status without native ending')
    if status == 0 and (final['terminated'] or final['truncated']):
        raise ValueError('running status at native ending')
    if instance['family'].startswith('boxoban-'):
        # The final native action pays only the terminal reward. Earlier
        # rewards telescope to the number of occupied fountains before it.
        running_steps = final['steps'] - int(status != 0)
        shaping = (final['return'] - int(status == 2) + .001 * running_steps) * 10
        occupied = round(shaping)
        if not 0 <= occupied <= min(3, running_steps) or not math.isclose(shaping, occupied, abs_tol=1e-7):
            raise ValueError('return inconsistent with native Boxoban shaping')
        return
    # Navigation and Quest use the native constant penalty for stalled turns.
    penalty = int(status == 2) - final['return']
    if not -1e-9 <= penalty <= .01 * final['steps'] + 1e-9 or not math.isclose(penalty * 100, round(penalty * 100), abs_tol=1e-7):
        raise ValueError('return inconsistent with native reward defaults')
