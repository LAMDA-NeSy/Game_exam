"""Trusted, stdlib-only game configuration; shared by preflight, sim and verifier."""
from config_schema import HASH, mapping, positive, validate_engine_versions

SCHEMA_VERSION = '1.0.0'
BENCHMARK = 'textworld'
FIELDS = {'engine_versions', 'challenge_settings', 'asset_sha256', 'max_score'}
METRICS = {'normalized_score', 'score', 'won', 'lost', 'native_moves'}
PROFILES = {'player-text-v2'}
REDUCERS = {('family_macro', '1.0.0')}


def validate(value):
    validate_engine_versions(value['engine_versions'], {'textworld': '1.7.0', 'jericho': '3.3.1', 'numpy': '1.26.4'})
    positive(value['max_score'], 'max_score')
    assets = value['asset_sha256']
    mapping(assets, {'game.z8', 'game.json'}, label='asset_sha256')
    if any(not isinstance(v, str) or not HASH.fullmatch(v) for v in assets.values()):
        raise ValueError('invalid asset digest')
    if not isinstance(value['challenge_settings'], dict):
        raise TypeError('challenge_settings must be an object')
