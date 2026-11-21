"""Trusted Chess configuration, usable without native dependencies."""
from config_schema import validate_engine_versions

BENCHMARK = 'chess'
SCHEMA_VERSION = '1.0.0'
ENV_ID = 'classic/chess-v6'
PROFILE = 'chess-public-board-native-v1'
PROFILES = {PROFILE}
METRICS = {'match_points'}
REDUCERS = {('family_macro', '1.0.0')}
FIELDS = {'engine_versions', 'engine_commit', 'engine_wheel_sha256', 'controlled_agent',
          'initialization_policy', 'opponent_policy', 'opponent_seed', 'tool_policy'}
VERSIONS = {'pettingzoo': '1.27.0', 'chess': '1.11.2', 'gymnasium': '1.0.0',
            'numpy': '1.26.4', 'pygame-ce': '2.5.6'}
COMMIT = '7221e4b15873a8b16555fda038a77a6ae595e88d'
WHEEL = '075a6ab7c32d32d9a674f1af395010198bf09c172341aa38fa5415461601ac61'


def validate(value):
    validate_engine_versions(value['engine_versions'], VERSIONS)
    expected = {
        'env_id': ENV_ID, 'family': 'standard-start', 'controlled_agent': 'player_0',
        'initialization_policy': 'native-start-v1', 'opponent_policy': 'hash-legal-v1',
        'engine_commit': COMMIT, 'engine_wheel_sha256': WHEEL,
        'tool_policy': 'public-tools-no-task-solutions-v1',
        'capabilities': {'images': False, 'action_mode': 'enum', 'timing': 'action-stepped',
                         'native_truncation': True},
        'metric_spec': {'primary': 'match_points', 'reducer': 'family_macro',
                        'reducer_version': '1.0.0', 'success_label': 'native_white_win'},
    }
    for field, frozen in expected.items():
        if value[field] != frozen:
            raise ValueError(f'unsupported Chess {field}')
    if type(value['opponent_seed']) is not int or not 0 <= value['opponent_seed'] < 2**31:
        raise ValueError('invalid Chess opponent seed')
    if value['max_steps'] is None:
        raise ValueError('Chess requires a public decision budget')
