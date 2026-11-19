"""Check VGC win/loss evidence against the trusted live verdict."""
import math


def validate_metrics(final, instance):
    metrics = final['metrics']
    win = metrics.get('win')
    if type(win) is not int or win not in (0, 1):
        raise ValueError('invalid native win flag')
    if final['success'] != bool(win):
        raise ValueError('inconsistent success flag')
    if 'completion_score' in metrics or instance['metric_spec']['primary'] == 'completion_score':
        score = metrics.get('completion_score')
        if type(score) is not int or score != 100 * win:
            raise ValueError('inconsistent completion score')
    if type(metrics.get('native_return')) not in (int, float) or not math.isfinite(metrics['native_return']):
        raise ValueError('invalid native return')
    if metrics['native_return'] != final['return']:
        raise ValueError('inconsistent native return')
    if type(metrics.get('native_steps')) is not int or metrics['native_steps'] != final['steps']:
        raise ValueError('inconsistent native action count')
