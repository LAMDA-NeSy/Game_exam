"""Trusted, stdlib-only game configuration; shared by preflight, sim and verifier."""
from config_schema import validate_engine_versions

SCHEMA_VERSION = '1.0.0'
BENCHMARK = 'crafter'
FIELDS = {'engine_versions', 'engine_patch', 'area', 'milestone', 'achievement_names', 'native_max_steps'}
METRICS = {'achievement_fraction', 'achievement_count', 'native_return', 'milestone_success', 'health'}
PROFILES = {'native-rgb-v1'}
REDUCERS = {('family_macro', '1.0.0'), ('crafter_achievements', '1.0.0')}


def validate(value):
    validate_engine_versions(value['engine_versions'], {'crafter': '1.8.3', 'numpy': '1.26.4', 'Pillow': '10.4.0', 'opensimplex': '0.4.5.1'})
    if value['engine_patch'] is not None or value['area'] != [64, 64]:
        raise ValueError('unsupported Crafter engine profile')
    names = value['achievement_names']
    if not isinstance(names, list) or len(names) != 22 or any(not isinstance(n, str) for n in names) or len(set(names)) != 22:
        raise ValueError('Crafter requires 22 distinct achievement names')
    if value['milestone'] not in names:
        raise ValueError('unknown milestone')
    if type(value['native_max_steps']) is not int or value['native_max_steps'] != 10000:
        raise ValueError('native Crafter length must remain 10000')
