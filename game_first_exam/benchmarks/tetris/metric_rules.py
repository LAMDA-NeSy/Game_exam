"""Validate native Tetris line and reward accounting."""


def validate_metrics(final, instance):
    metrics = final['metrics']
    expected = {'success', 'lines_cleared', 'native_return',
                'rewarded_placements', 'line_clear_score'}
    if set(metrics) != expected:
        raise ValueError('wrong Tetris metric fields')
    for key in ('success', 'lines_cleared', 'rewarded_placements', 'line_clear_score'):
        if type(metrics[key]) is not int or metrics[key] < 0:
            raise ValueError('invalid Tetris integer metric: ' + key)
    if metrics['success'] not in (0, 1):
        raise ValueError('invalid Tetris success metric')
    if metrics['native_return'] != final['return']:
        raise ValueError('inconsistent native Tetris return')
    if metrics['native_return'] != metrics['rewarded_placements'] + metrics['line_clear_score']:
        raise ValueError('inconsistent native Tetris reward accounting')
    success = metrics['lines_cleared'] >= instance['target_lines']
    if metrics['success'] != int(success) or final['success'] != (success and not final['sim_error']):
        raise ValueError('inconsistent Tetris target success')
    if final['steps'] == 0 and any(metrics[key] for key in expected):
        raise ValueError('Tetris metrics without an action')
    if final['truncated']:
        raise ValueError('Tetris declared no native truncation')
