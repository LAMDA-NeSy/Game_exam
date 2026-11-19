"""Stdlib-only validation of every frozen native level; no engine imports."""
import json
SCHEMA_VERSION = '1.0.0'
BENCHMARK = 'vmage_flappybird'
FROZEN_FIELDS = json.loads('{"archive_sha256": "1047daa50004003eb9848205e1c420679e51d54d9a38acd3155da4aa8680e919", "dt": 0.033, "engine_versions": {"Pillow": "10.4.0", "imageio": "2.36.0", "numpy": "2.2.4", "opencv-python": "4.11.0.86", "pygame": "2.6.1", "scipy": "1.15.1", "tqdm": "4.67.1"}, "fps": 30, "frame_ledger": "pygame-base-capture-asymmetry-v1", "frames_per_decision": 3, "initialization": "native-init_run-step-None-dt0-v1", "native_actions": ["UP", "DOWN", "KEEP"], "native_frame_limit": null, "native_game": "flappybird", "native_level": 1, "native_level_sha256": "cd3d8ce00a3725c3113fc2c2efe4e54f7dec8cf05609b93c859b21d0cc0bbbe9", "native_settings_sha256": "6f411925aa489f791e77c02ab5628d9164272488806e6d34960988b35aec9f7a", "observation_size": [202, 360], "passive_action": null, "python_version": "3.10.12", "sdl_version": "2.28.4", "source_manifest_sha256": "c78f261627da52a3a64a8381c66ad678553e015482d6c815db645d6df4a6da4d", "surface_size": [576, 1024], "upstream_commit": "95d5d4a445bb0b75cce765c93107d87f84613e4d"}')
LEVEL_FIELDS = json.loads('{"1": {"frames_per_decision": 3, "native_actions": ["UP", "DOWN", "KEEP"], "native_frame_limit": null, "native_level": 1, "native_level_sha256": "cd3d8ce00a3725c3113fc2c2efe4e54f7dec8cf05609b93c859b21d0cc0bbbe9", "observation_size": [202, 360], "passive_action": null, "surface_size": [576, 1024]}, "2": {"frames_per_decision": 3, "native_actions": ["UP", "DOWN", "KEEP"], "native_frame_limit": null, "native_level": 2, "native_level_sha256": "e1b0fd409cf18c5922248b04d2eeceb3c85cea78c7630daba38f5bcd6478be34", "observation_size": [202, 360], "passive_action": null, "surface_size": [576, 1024]}, "3": {"frames_per_decision": 3, "native_actions": ["UP", "DOWN", "KEEP"], "native_frame_limit": null, "native_level": 3, "native_level_sha256": "1eb93f5afd359a79cb6919da1ed2fb0d2f5f042a959b4a47a066a18bad093501", "observation_size": [202, 360], "passive_action": null, "surface_size": [576, 1024]}, "4": {"frames_per_decision": 3, "native_actions": ["UP", "KEEP", "NONE"], "native_frame_limit": null, "native_level": 4, "native_level_sha256": "7298dff24e0453d3aa21f8b403ccdc94eb884124ea8b60880205bf64b374502a", "observation_size": [202, 360], "passive_action": null, "surface_size": [576, 1024]}, "5": {"frames_per_decision": 3, "native_actions": ["UP", "KEEP", "NONE"], "native_frame_limit": null, "native_level": 5, "native_level_sha256": "b3b94e27cc69d1bb41e4e8e55bb45fd445a3ddf116c822f04693d97f1433ca35", "observation_size": [202, 360], "passive_action": null, "surface_size": [576, 1024]}, "6": {"frames_per_decision": 3, "native_actions": ["UP", "KEEP", "NONE"], "native_frame_limit": null, "native_level": 6, "native_level_sha256": "2111389b57832815765dbba253bbb2a2ef2a21dfe22c8f3642ee10146d3abf8d", "observation_size": [202, 360], "passive_action": null, "surface_size": [576, 1024]}, "7": {"frames_per_decision": 3, "native_actions": ["UP", "NONE"], "native_frame_limit": null, "native_level": 7, "native_level_sha256": "3d600dbf9a777f900716949d4830ba2d521eb39cadc2d21cdae020b5c0055bb2", "observation_size": [202, 360], "passive_action": null, "surface_size": [576, 1024]}}')
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
    if value['adapter_version'] != '1.0.0' or value['benchmark'] != BENCHMARK or value['env_id'] != 'V-MAGE-FlappyBird' + '-L' + str(level) + '-v2' or value['family'] != f'l{level:02}':
        raise ValueError('unsupported native game identity/version')
    if type(value['seed']) is not int or value['seed'] != 0 or value['max_steps'] is not None:
        raise ValueError('only seed0 without an extra action cap is frozen')
    if value['observation_profile'] != 'vmage-rgb-h360-v1':
        raise ValueError('unsupported native observation profile')
    if value['capabilities'] != {'images': True, 'action_mode': 'enum', 'timing': 'action-stepped', 'native_truncation': False}:
        raise ValueError('unsupported native capabilities')
    if value['metric_spec'] != {'primary': 'native_score', 'reducer': 'family_macro', 'reducer_version': '1.0.0', 'success_label': 'positive_score_auxiliary'}:
        raise ValueError('unsupported V-MAGE metric specification')
