"""Trusted stdlib-only schema for the native Gymnasium 2048 profile."""
from config_schema import validate_engine_versions

SCHEMA_VERSION = '1.0.0'
BENCHMARK = 'game2048'
FIELDS = {'engine_versions', 'board_size', 'native_max_power',
          'native_render_shape', 'target_power'}
METRICS = {'target_reached', 'native_score', 'max_tile', 'valid_moves',
           'invalid_moves', 'native_return'}
PROFILES = {'native-rgb-board-score-v1'}
REDUCERS = {('family_macro', '1.0.0')}
ENGINE_VERSIONS = {
    'gymnasium-2048': '0.1.2',
    'gymnasium': '1.3.0',
    'numpy': '1.26.4',
    'pygame': '2.6.1',
}


def validate(value):
    validate_engine_versions(value['engine_versions'], ENGINE_VERSIONS)
    if (value['env_id'] != 'gymnasium_2048/TwentyFortyEight-v0'
            or value['family'] != '2048-classic'):
        raise ValueError('unsupported 2048 environment/family')
    if value['board_size'] != 4 or value['native_max_power'] != 16:
        raise ValueError('unsupported native 2048 board profile')
    if value['native_render_shape'] != [460, 400, 3]:
        raise ValueError('unsupported native 2048 render profile')
    if value['target_power'] != 11:
        raise ValueError('the supported target is the native 2048 tile')
    if type(value['max_steps']) is not int or not 1 <= value['max_steps'] <= 10000:
        raise ValueError('2048 requires a public action cap in [1, 10000]')
    if value['capabilities'] != {'images': True, 'action_mode': 'enum',
                                 'timing': 'action-stepped', 'native_truncation': False}:
        raise ValueError('unsupported 2048 capabilities')
    if value['metric_spec'] != {'primary': 'native_score', 'reducer': 'family_macro',
                                'reducer_version': '1.0.0',
                                'success_label': '2048_tile_reached'}:
        raise ValueError('unsupported 2048 scoring profile')
