"""Trusted MiniHack configuration; no native engine imports."""
from config_schema import validate_engine_versions

SCHEMA_VERSION = '1.0.0'
BENCHMARK = 'minihack'
FIELDS = {'engine_versions', 'engine_commit', 'engine_archive_sha256', 'native_max_steps', 'native_seed_policy', 'native_clock'}
METRICS = {'success', 'native_return', 'completion_score'}
QUEST_PROFILE = 'player-crop-inventory-9x9-v1'
PROFILES = {'native-observation-v1', 'player-crop-9x9-v1', QUEST_PROFILE}
REDUCERS = {('family_macro', '1.0.0')}
TASKS = {
    'MiniHack-Room-5x5-v0': ('room', 100),
    'MiniHack-River-v0': ('river', 350),
    'MiniHack-MazeWalk-9x9-v0': ('mazewalk-9x9', 200),
    'MiniHack-MazeWalk-15x15-v0': ('mazewalk-15x15', 1000),
    'MiniHack-Corridor-R3-v0': ('corridor-r3', 1000),
    'MiniHack-CorridorBattle-Dark-v0': ('corridorbattle-dark', 350),
    'MiniHack-Quest-Easy-v0': ('quest-easy', 500),
    'MiniHack-Quest-Medium-v0': ('quest-medium', 1000),
    'MiniHack-Boxoban-Medium-v0': ('boxoban-medium', 400),
    'MiniHack-Boxoban-Hard-v0': ('boxoban-hard', 400),
}
COMMIT = '95b11cc8db68d72a7fe6e7540e75b568b7a811d8'
ARCHIVE_SHA256 = '8a277171302b0b5b34633001283cdff5aa8eaeadb940256df02c8fdae67a48eb'


def validate(value):
    if value['native_clock'] != {'start_utc': '2026-11-13T12:00:00Z', 'implementation': 'libfaketime',
                                  'version': '0.9.12', 'monotonic': 'real',
                                  'source_sha256': '4fc32218697c052adcdc5ee395581f2554ca56d086ac817ced2be0d6f1f8a9fa'}:
        raise ValueError('unsupported native calendar clock')
    validate_engine_versions(value['engine_versions'], {'minihack': '1.0.2', 'nle': '1.1.0', 'gymnasium': '1.0.0', 'numpy': '1.26.4'})
    if value['engine_commit'] != COMMIT or value['engine_archive_sha256'] != ARCHIVE_SHA256:
        raise ValueError('unsupported MiniHack source')
    if value['env_id'] not in TASKS or (value['family'], value['native_max_steps']) != TASKS[value['env_id']]:
        raise ValueError('unsupported native MiniHack task/defaults')
    if (value['observation_profile'] == QUEST_PROFILE) != value['family'].startswith('quest-'):
        raise ValueError('Quest requires the native inventory observation profile')
    if value['family'].startswith('boxoban-') and value['observation_profile'] != 'native-observation-v1':
        raise ValueError('Boxoban requires the native premapped board profile')
    if type(value['native_max_steps']) is not int or value['max_steps'] is not None:
        raise ValueError('preserve native MiniHack episode limits without an extra action cap')
    reset_policy = 'boxoban-native-reset-v1' if value['family'].startswith('boxoban-') else 'gym-reset-seed-v1'
    if value['native_seed_policy'] != 'core=disp=instance.seed;reseed=false;' + reset_policy:
        raise ValueError('unsupported native seed policy')
