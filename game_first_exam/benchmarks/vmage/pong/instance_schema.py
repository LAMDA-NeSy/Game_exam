"""Stdlib-only validation of every frozen native level; no engine imports."""
import json
SCHEMA_VERSION = '1.0.0'
BENCHMARK = 'vmage_pong'
FROZEN_FIELDS = json.loads('{"archive_sha256": "1047daa50004003eb9848205e1c420679e51d54d9a38acd3155da4aa8680e919", "dt": 0.033, "engine_versions": {"Pillow": "10.4.0", "imageio": "2.36.0", "numpy": "2.2.4", "opencv-python": "4.11.0.86", "pygame": "2.6.1", "scipy": "1.15.1", "tqdm": "4.67.1"}, "fps": 30, "frame_ledger": "pygame-base-capture-asymmetry-v1", "frames_per_decision": 3, "initialization": "native-init_run-step-None-dt0-v1", "native_actions": ["LEFTUP", "LEFTDOWN", "RIGHTUP", "RIGHTDOWN", "NONE"], "native_frame_limit": null, "native_game": "pong", "native_level": 1, "native_level_sha256": "92198287e5fbfd1b89e9cd0cba5aae9a760974df3d638a3f92ac281ee5cf588e", "native_settings_sha256": "3a132049606e1d5f4c03db318b7b94a28b3aaec2e12183c487971c806f1d2609", "observation_size": [480, 360], "passive_action": null, "python_version": "3.10.12", "sdl_version": "2.28.4", "source_manifest_sha256": "c78f261627da52a3a64a8381c66ad678553e015482d6c815db645d6df4a6da4d", "surface_size": [800, 600], "upstream_commit": "95d5d4a445bb0b75cce765c93107d87f84613e4d"}')
LEVEL_FIELDS = json.loads('{"1": {"frames_per_decision": 3, "native_actions": ["LEFTUP", "LEFTDOWN", "RIGHTUP", "RIGHTDOWN", "NONE"], "native_frame_limit": null, "native_level": 1, "native_level_sha256": "92198287e5fbfd1b89e9cd0cba5aae9a760974df3d638a3f92ac281ee5cf588e", "observation_size": [480, 360], "passive_action": null, "surface_size": [800, 600]}, "2": {"frames_per_decision": 3, "native_actions": ["LEFTUP", "LEFTDOWN", "RIGHTUP", "RIGHTDOWN", "NONE"], "native_frame_limit": null, "native_level": 2, "native_level_sha256": "5c89c899526d1baac1d55c0be14a338666abbf877ce9b78cf4dc162a55a68a95", "observation_size": [480, 360], "passive_action": null, "surface_size": [800, 600]}, "3": {"frames_per_decision": 3, "native_actions": ["LEFTUP", "LEFTDOWN", "RIGHTUP", "RIGHTDOWN", "NONE"], "native_frame_limit": null, "native_level": 3, "native_level_sha256": "e5184af55b1af04c56124d5f7da6535c36aa3383f1a561d1edd4f656ea56fc45", "observation_size": [480, 360], "passive_action": null, "surface_size": [800, 600]}}')
FIELDS = set(FROZEN_FIELDS)
METRICS = {'native_score'}
PROFILES = {'vmage-rgb-h360-v1'}
REDUCERS = {('family_macro', '1.0.0')}
COMMON = {'schema_version', 'protocol', 'adapter_version', 'capabilities', 'benchmark', 'env_id', 'family', 'seed', 'max_steps', 'initial_state_sha256', 'observation_profile', 'metric_spec'}

def validate(value):
    if not isinstance(value, dict) or set(value) != COMMON | FIELDS:
        raise ValueError('V-MAGE instance fields differ from frozen schema')
    level = value.get('native_level')
    if type(level) is not int or str(level) not in LEVEL_FIELDS:
        raise ValueError('unsupported native V-MAGE level')
    expected_fields = dict(FROZEN_FIELDS, **LEVEL_FIELDS[str(level)])
    for key, expected in expected_fields.items():
        if type(value[key]) is not type(expected) or json.dumps(value[key], sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
            raise ValueError('unsupported frozen V-MAGE field: ' + key)
    if value['adapter_version'] != '1.0.0' or value['benchmark'] != BENCHMARK or value['env_id'] != 'V-MAGE-Pong' + '-L' + str(level) + '-v2' or value['family'] != f'l{level:02}':
        raise ValueError('unsupported native game identity/version')
    if type(value['seed']) is not int or value['seed'] != 0 or value['max_steps'] is not None:
        raise ValueError('only seed0 without an extra action cap is frozen')
    if value['observation_profile'] != 'vmage-rgb-h360-v1':
        raise ValueError('unsupported native observation profile')
    if value['capabilities'] != {'images': True, 'action_mode': 'enum', 'timing': 'action-stepped', 'native_truncation': False}:
        raise ValueError('unsupported native capabilities')
    if value['metric_spec'] != {'primary': 'native_score', 'reducer': 'family_macro', 'reducer_version': '1.0.0', 'success_label': 'positive_score_auxiliary'}:
        raise ValueError('unsupported V-MAGE metric specification')
