"""Trusted stdlib-only schema for the frozen CoinRun profile."""
from config_schema import validate_engine_versions

SCHEMA_VERSION = '1.0.0'
BENCHMARK = 'coinrun'
FIELDS = {'engine_versions', 'distribution_mode', 'native_max_steps'}
METRICS = {'success', 'completion_score', 'native_return'}
PROFILES = {'native-rgb-64-v1'}
REDUCERS = {('family_macro', '1.0.0')}
ENGINE_VERSIONS = {'procgen': '0.10.7', 'gym3': '0.3.3', 'numpy': '1.26.4'}


def validate(value):
    validate_engine_versions(value['engine_versions'], ENGINE_VERSIONS)
    if value['env_id'] != 'procgen-coinrun-v0':
        raise ValueError('unsupported native CoinRun environment')
    mode = value['distribution_mode']
    if mode not in {'easy', 'hard'} or value['family'] != 'coinrun-' + mode:
        raise ValueError('unsupported CoinRun difficulty/family')
    if value['capabilities'] != {'images': True, 'action_mode': 'enum',
                                 'timing': 'action-stepped', 'native_truncation': False}:
        raise ValueError('unsupported CoinRun capabilities')
    if value['max_steps'] is not None:
        raise ValueError('preserve native CoinRun episode limit')
    if type(value['native_max_steps']) is not int or value['native_max_steps'] != 1000:
        raise ValueError('unsupported native CoinRun timeout')
    if value['metric_spec'] != {'primary': 'completion_score', 'reducer': 'family_macro',
                                'reducer_version': '1.0.0', 'success_label': 'native_level_complete'}:
        raise ValueError('unsupported CoinRun scoring profile')
