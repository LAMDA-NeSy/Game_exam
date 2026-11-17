"""Trusted VGC configuration; no native engine imports.

The frozen instance pins one regulation, both teams, the fixed opponent policy and
the engine versions. Unknown fields, profiles, opponents or reducers are rejected
before any engine is constructed.
"""
from config_schema import validate_engine_versions

SCHEMA_VERSION = '1.0.0'
BENCHMARK = 'vgc'

# Game-specific instance fields beyond the common set (config_schema.COMMON).
FIELDS = {
    'reg',
    'team1',
    'team2',
    'opponent_policy',
    'engine_versions',
    'engine_commit',
    'battle_format',
}

METRICS = {'win', 'completion_score', 'native_return', 'native_steps'}

# One observation profile for now: the native 12-chunk vector, JSON-serialized.
PROFILES = {'native-vector-v1'}

REDUCERS = {('vgc_win_rate', '1.0.0')}

REGS = {'ma', 'mb'}
OPPONENTS = {'random', 'max_base_power', 'simple_heuristics'}
FORMATS = {
    'ma': 'gen9championsvgc2026regma',
    'mb': 'gen9championsvgc2026regmb',
}

# Pin the poke-env fork and engine. Fill after a clean install (pip freeze / importlib.metadata).
# Expected values are exact strings; see SOURCE.json for the upstream commit.
ENGINE_VERSIONS = {
    'poke-env': 'TODO_PIN_POKE_ENV_VERSION',
}
ENGINE_COMMIT = 'TODO_PIN_POKE_ENV_COMMIT'


def validate(value):
    if value['reg'] not in REGS:
        raise ValueError('unsupported VGC regulation')
    if value['battle_format'] != FORMATS[value['reg']]:
        raise ValueError('battle_format disagrees with regulation')
    if value['opponent_policy'] not in OPPONENTS:
        raise ValueError('unsupported opponent policy')
    for key in ('team1', 'team2'):
        if not isinstance(value[key], str) or not value[key].strip():
            raise ValueError(f'{key} must be a nonempty Showdown team string')
    if value['team1'].strip() == value['team2'].strip():
        raise ValueError('mirror matchup is not a distinct frozen instance')
    validate_engine_versions(value['engine_versions'], ENGINE_VERSIONS)
    if value['engine_commit'] != ENGINE_COMMIT:
        raise ValueError('unsupported poke-env fork commit')
    # standard mode has no public action cap beyond the native battle turn limit.
    if value['max_steps'] is not None:
        raise ValueError('preserve the native battle limit without an extra action cap')
    if value['capabilities']['action_mode'] != 'text':
        raise ValueError('VGC joint actions use the text action grammar')
