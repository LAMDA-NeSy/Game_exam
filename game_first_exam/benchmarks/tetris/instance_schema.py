"""Trusted stdlib-only schema for the native Tetris Gymnasium profile."""
from config_schema import validate_engine_versions

SCHEMA_VERSION = '1.0.0'
BENCHMARK = 'tetris'
FIELDS = {'engine_versions', 'board_width', 'board_height', 'gravity',
          'native_queue_size', 'native_holder_size', 'target_lines'}
METRICS = {'success', 'lines_cleared', 'native_return', 'rewarded_placements', 'line_clear_score'}
PROFILES = {'native-rgb-board-queue-holder-v1'}
REDUCERS = {('family_macro', '1.0.0')}
ENGINE_VERSIONS = {
    'tetris-gymnasium': '0.2.1',
    'gymnasium': '1.4.0',
    'numpy': '1.26.4',
    'opencv-python': '4.10.0.84',
}


def validate(value):
    validate_engine_versions(value['engine_versions'], ENGINE_VERSIONS)
    if value['env_id'] != 'tetris_gymnasium/Tetris' or value['family'] != 'tetris-classic':
        raise ValueError('unsupported Tetris environment/family')
    if value['seed'] < 1:
        # Upstream 0.2.1 treats seed=0 as an unseeded reset.
        raise ValueError('Tetris seed must be positive')
    if (value['board_width'], value['board_height'], value['gravity']) != (10, 20, True):
        raise ValueError('unsupported Tetris board or gravity profile')
    if (value['native_queue_size'], value['native_holder_size']) != (4, 1):
        raise ValueError('unsupported native queue/holder profile')
    if type(value['target_lines']) is not int or not 1 <= value['target_lines'] <= 1000:
        raise ValueError('target_lines must be an integer in [1, 1000]')
    if value['max_steps'] is None:
        raise ValueError('Tetris requires a public action cap')
    if value['capabilities'] != {'images': True, 'action_mode': 'enum',
                                 'timing': 'action-stepped', 'native_truncation': False}:
        raise ValueError('unsupported Tetris capabilities')
    if value['metric_spec'] != {'primary': 'lines_cleared', 'reducer': 'family_macro',
                                'reducer_version': '1.0.0',
                                'success_label': 'target_lines_reached'}:
        raise ValueError('unsupported Tetris scoring profile')
