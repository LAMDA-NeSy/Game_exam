"""Frozen native match conditions, validated without importing Java or pyftg."""
from config_schema import validate_engine_versions

SCHEMA_VERSION = '1.0.0'
BENCHMARK = 'fightingice'
FIELDS = {'engine_versions', 'player', 'characters', 'opponent', 'rounds', 'round_frames', 'initial_hp', 'native_seed_policy'}
METRICS = {'round_win_score'}
PROFILES = {'native-delayed-framedata-v1'}
REDUCERS = {('family_macro', '1.0.0')}


def validate(value):
    validate_engine_versions(value['engine_versions'], {'fightingice': '7.0', 'pyftg': '2.3'})
    if type(value['player']) is not int or value['player'] not in (0, 1):
        raise ValueError('player must be the native zero-based side')
    if value['characters'] != ['ZEN', 'ZEN'] or value['opponent'] != 'pyftg-kick-b-v1':
        raise ValueError('unsupported frozen character/opponent')
    for name, expected in [('rounds', 3), ('round_frames', 3600), ('initial_hp', 400)]:
        if type(value[name]) is not int or value[name] != expected:
            raise ValueError('preserve native match limits: ' + name)
    if value['env_id'] != 'DareFightingICE-ZEN-KickAI-v7.0' or value['family'] != 'zen-kick':
        raise ValueError('unknown native match')
    if value['seed'] != 0 or value['native_seed_policy'] != 'no-native-seed;deterministic-opponent':
        raise ValueError('no native reset seed API is claimed')
    if value['max_steps'] is not None:
        raise ValueError('use native round limits, not a new public action cap')
    if value['metric_spec'] != {'primary': 'round_win_score', 'reducer': 'family_macro',
                                'reducer_version': '1.0.0', 'success_label': 'match_won'}:
        raise ValueError('unsupported FightingICE scoring profile')
    if value['capabilities'] != {'images': False, 'action_mode': 'enum',
                                  'timing': 'action-stepped', 'native_truncation': False}:
        raise ValueError('unsupported FightingICE capabilities')
