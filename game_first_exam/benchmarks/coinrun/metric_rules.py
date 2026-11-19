"""CoinRun completion and return consistency for the isolated verifier."""


def validate_metrics(final, instance):
    metrics = final['metrics']
    success = final['success']
    expected = {'success': int(success), 'completion_score': 100 * int(success),
                'native_return': final['return'], 'native_steps': final['steps'],
                'native_episode_ended': final['terminated']}
    if metrics != expected:
        raise ValueError('inconsistent CoinRun metrics')
    if (type(metrics['success']) is not int or type(metrics['completion_score']) is not int
            or type(metrics['native_steps']) is not int
            or type(metrics['native_episode_ended']) is not bool):
        raise ValueError('invalid CoinRun metric types')
    if final['truncated'] or (success and not final['terminated']):
        raise ValueError('inconsistent CoinRun episode boundary')
    if final['return'] != (10.0 if success else 0.0):
        raise ValueError('inconsistent native CoinRun reward')
    if not 0 <= final['steps'] <= instance['native_max_steps']:
        raise ValueError('inconsistent native CoinRun action limit')
    if final['steps'] == instance['native_max_steps'] and not final['terminated']:
        raise ValueError('native CoinRun timeout must end the episode')
