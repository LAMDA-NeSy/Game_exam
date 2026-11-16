"""Trusted, stdlib-only game configuration; shared by preflight, sim and verifier."""
from config_schema import validate_engine_versions

SCHEMA_VERSION = '1.0.0'
BENCHMARK = 'babaisai'
FIELDS = {'engine_versions', 'engine_commit', 'native_max_steps'}
METRICS = {'success', 'native_return'}
PROFILES = {'native-rgb-v1'}
REDUCERS = {('family_macro', '1.0.0')}


def validate(value):
    validate_engine_versions(value['engine_versions'], {'gym': '0.25.0', 'numpy': '1.26.4', 'opencv-python': '4.11.0.86'})
    if value['engine_commit'] != '40ae1b29dbc67f2ecea06cc161ed5ca51719e5e3':
        raise ValueError('unsupported Baba engine commit')
    if type(value['native_max_steps']) is not int or value['native_max_steps'] < 1:
        raise ValueError('invalid native step limit')
    if value['env_id'] not in {'env/goto_win', 'env/two_room-break_stop-make_win'}:
        raise ValueError('unregistered Baba task')
