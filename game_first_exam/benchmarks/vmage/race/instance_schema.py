"""Stdlib-only validation of every frozen native level; no engine imports."""
import json
SCHEMA_VERSION = '1.0.0'
BENCHMARK = 'vmage_race'
FROZEN_FIELDS = json.loads('{"archive_sha256": "1047daa50004003eb9848205e1c420679e51d54d9a38acd3155da4aa8680e919", "dt": 0.033, "engine_versions": {"Pillow": "10.4.0", "imageio": "2.36.0", "numpy": "2.2.4", "opencv-python": "4.11.0.86", "pygame": "2.6.1", "scipy": "1.15.1", "tqdm": "4.67.1"}, "fps": 30, "frame_ledger": "pygame-base-capture-asymmetry-v1", "frames_per_decision": 3, "initialization": "native-init_run-step-None-dt0-v1", "native_actions": ["LEFT", "RIGHT", "UP", "DOWN"], "native_frame_limit": 100, "native_game": "race", "native_level": 1, "native_level_sha256": "b921de201d2a84449b7cfea344ae355972e925d6cf4652e0949b6493ecdaeded", "native_settings_sha256": "49793fdafb10c9661dfa8c9b8219a0a84e17d2c4b922d29ed8c96e2d54328aed", "observation_size": [480, 360], "passive_action": null, "python_version": "3.10.12", "sdl_version": "2.28.4", "source_manifest_sha256": "c78f261627da52a3a64a8381c66ad678553e015482d6c815db645d6df4a6da4d", "surface_size": [1024, 768], "upstream_commit": "95d5d4a445bb0b75cce765c93107d87f84613e4d"}')
LEVEL_FIELDS = json.loads('{"1": {"frames_per_decision": 3, "native_actions": ["LEFT", "RIGHT", "UP", "DOWN"], "native_frame_limit": 100, "native_level": 1, "native_level_sha256": "b921de201d2a84449b7cfea344ae355972e925d6cf4652e0949b6493ecdaeded", "observation_size": [480, 360], "passive_action": null, "surface_size": [1024, 768]}, "2": {"frames_per_decision": 3, "native_actions": ["LEFT", "RIGHT", "UP", "DOWN"], "native_frame_limit": 150, "native_level": 2, "native_level_sha256": "0711e72387f300d4bd4b6a851e68e2fcaeb9f83c2fe1453f0df4ddb8e62d0699", "observation_size": [480, 360], "passive_action": null, "surface_size": [1024, 768]}, "3": {"frames_per_decision": 3, "native_actions": ["LEFT", "RIGHT", "UP", "DOWN"], "native_frame_limit": 150, "native_level": 3, "native_level_sha256": "355cc29339fe4d9eea47dc998f2c420a70fda2c19edc5f82b4bda1e3071b9e1b", "observation_size": [480, 360], "passive_action": null, "surface_size": [1024, 768]}, "4": {"frames_per_decision": 3, "native_actions": ["LEFT", "RIGHT", "FORWARD", "BACKWARD"], "native_frame_limit": 150, "native_level": 4, "native_level_sha256": "1981bb851013ec64f6ac19feda5afaa12d52e713907e11c48c71b7d8ae9ddd69", "observation_size": [480, 360], "passive_action": null, "surface_size": [1024, 768]}, "5": {"frames_per_decision": 3, "native_actions": ["LEFT", "RIGHT", "FORWARD", "BACKWARD"], "native_frame_limit": 150, "native_level": 5, "native_level_sha256": "875e730543be80e2c61977e7ce5fd876c21c5ea2d8467bfb3f5656259aae16b8", "observation_size": [480, 360], "passive_action": null, "surface_size": [1024, 768]}, "6": {"frames_per_decision": 3, "native_actions": ["FORWARD", "BACKWARD", "LEFT", "RIGHT"], "native_frame_limit": 100, "native_level": 6, "native_level_sha256": "373fdc87aee0bd253bd8b4e3162902f3e2582170856f42d08bc1d3bdc4d4f0bb", "observation_size": [480, 360], "passive_action": null, "surface_size": [1024, 768]}, "7": {"frames_per_decision": 3, "native_actions": ["FORWARD", "BACKWARD", "LEFT", "RIGHT"], "native_frame_limit": 100, "native_level": 7, "native_level_sha256": "36675492156bd1003c91f08a80bb179c70a17b0f8c60e80ff3bf9d5341c41b5e", "observation_size": [480, 360], "passive_action": null, "surface_size": [1024, 768]}, "8": {"frames_per_decision": 3, "native_actions": ["FORWARD", "BACKWARD", "LEFT", "RIGHT"], "native_frame_limit": 300, "native_level": 8, "native_level_sha256": "fd90f6f1ac8a443645487a398fc371f5539cb26974946e7433b8016758e80f75", "observation_size": [480, 360], "passive_action": null, "surface_size": [1024, 768]}, "9": {"frames_per_decision": 3, "native_actions": ["FORWARD", "BACKWARD", "LEFT", "RIGHT"], "native_frame_limit": 500, "native_level": 9, "native_level_sha256": "89373304d6b97c75396515eec9fd5271b021ed9c0cbc0a9764ce9dcdf23c8abc", "observation_size": [480, 360], "passive_action": null, "surface_size": [1024, 768]}}')
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
    if value['adapter_version'] != '1.0.0' or value['benchmark'] != BENCHMARK or value['env_id'] != 'V-MAGE-Race' + '-L' + str(level) + '-v2' or value['family'] != f'l{level:02}':
        raise ValueError('unsupported native game identity/version')
    if type(value['seed']) is not int or value['seed'] != 0 or value['max_steps'] is not None:
        raise ValueError('only seed0 without an extra action cap is frozen')
    if value['observation_profile'] != 'vmage-rgb-h360-v1':
        raise ValueError('unsupported native observation profile')
    if value['capabilities'] != {'images': True, 'action_mode': 'enum', 'timing': 'action-stepped', 'native_truncation': True}:
        raise ValueError('unsupported native capabilities')
    if value['metric_spec'] != {'primary': 'native_score', 'reducer': 'family_macro', 'reducer_version': '1.0.0', 'success_label': 'native_goal_reached'}:
        raise ValueError('unsupported V-MAGE metric specification')
