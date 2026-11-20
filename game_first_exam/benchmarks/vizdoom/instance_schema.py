"""Frozen ViZDoom scenario profiles shared by the host, simulator and verifier."""
from config_schema import validate_engine_versions

SCHEMA_VERSION = "1.0.0"
BENCHMARK = "vizdoom"
STANDARD_CLIENT = "vizdoom_client.py"
FIELDS = {"engine_versions", "engine_commit", "scenario_hashes", "start_tic",
          "timeout_tics", "tics_per_decision", "buttons"}
METRICS = {"objective_success", "native_return"}
PER_SCENARIO_METRICS = {"native_return"}
PROFILES = {"rgb-first-person-v1", "rgb-notifications-v1"}
REDUCERS = {("family_macro", "1.0.0")}
ENGINE_COMMIT = "53d758a64f113ef3ef8f67bea5b4b717e51e1c0a"
ENGINE_VERSIONS = {"vizdoom": "1.3.2", "numpy": "2.5.5"}
COMMON_ASSETS = {
    "freedoom2.wad": "a8772e088847032510d97ba2312406a6998f21cbab44d4ff10696faa9c0ecd4b",
    "vizdoom.pk3": "24381138aede0ab03a4266f8fdd0225a1819658f004d37c9dc349e006b74f34e",
}
SCENARIOS = {
    "basic": {
        "goal": "kill", "stem": "basic", "start_tic": 14, "timeout_tics": 300,
        "buttons": ["MOVE_LEFT", "MOVE_RIGHT", "ATTACK"],
        "cfg": "306ce424442279a1e5d98a75c36a900b616c2496dcdac93a2923946049c926e7",
        "wad": "fd0b7e5e2422e09288c786e7fc32181bb8ee4a3faa613a75ef88a3e39b5ce94e",
    },
    "my-way-home": {
        "goal": "green-vest", "stem": "my_way_home", "start_tic": 10, "timeout_tics": 2100,
        "buttons": ["TURN_LEFT", "TURN_RIGHT", "MOVE_FORWARD", "MOVE_LEFT", "MOVE_RIGHT"],
        "cfg": "3dc0eb5e3557df7918484f91bdc4bc13b78cf67c6a6eaf2052e8ad66cfccbe46",
        "wad": "18e98ff4c9186808eb00696b799cfe88a79e7486429c1692aafbed8ef359c0b1",
    },
    'basic-notifications': {'stem': 'basic_notifications',
     'goal': 'correct-target',
     'start_tic': 14,
     'timeout_tics': 300,
     'buttons': ['MOVE_LEFT', 'MOVE_RIGHT', 'ATTACK'],
     'cfg': '172233cb048bcd67a5c112378ced33e270d4b0ad6455be7fac29276dee5a36a6',
     'wad': 'c4b4bdc9c32c1244c080dac9381363f9b70e9bcb87edab3e4feed109b8f7f4ca',
     'observation_profile': 'rgb-notifications-v1'},
    'predict-position': {'stem': 'predict_position',
     'goal': 'kill',
     'start_tic': 16,
     'timeout_tics': 300,
     'buttons': ['TURN_LEFT', 'TURN_RIGHT', 'ATTACK'],
     'cfg': '5e97217a17d5285d80c9c7351cb69562c5ff005423780c352e5c507951e08f6f',
     'wad': 'a5a1bdbbfdbef2a505b496f6889d06751ba3431a50ec382fb303fcc4066917a6'},
    'deadly-corridor': {'stem': 'deadly_corridor',
     'goal': 'green-vest',
     'start_tic': 1,
     'timeout_tics': 2100,
     'buttons': ['MOVE_LEFT',
                 'MOVE_RIGHT',
                 'ATTACK',
                 'MOVE_FORWARD',
                 'MOVE_BACKWARD',
                 'TURN_LEFT',
                 'TURN_RIGHT'],
     'cfg': 'b76c53ad90ff27680c4a4655c88dc04458f2d597baac6cec5d38df91ca67c17a',
     'wad': '3c868f88c78df8219a2c41a2695ae04e5a19d60a32f1718282b3bbc7f20951ca'},
    'defend-center': {'stem': 'defend_the_center',
     'goal': None,
     'start_tic': 10,
     'timeout_tics': 2100,
     'buttons': ['TURN_LEFT', 'TURN_RIGHT', 'ATTACK'],
     'cfg': 'dd01c3d8041c282c9002540eecb6ddb264aebabaa9aaf24804a10c933587133c',
     'wad': 'eb3f8d3b3f456bbef32a1d41f847189dd83cc1d4e320157ba92b75a9b0d8d5bb',
     'stats': ('KILLCOUNT', 'HEALTH', 'AMMO2')},
    'defend-line': {'stem': 'defend_the_line',
     'goal': None,
     'start_tic': 10,
     'timeout_tics': 0,
     'buttons': ['TURN_LEFT', 'TURN_RIGHT', 'ATTACK'],
     'cfg': '3cb32d16a101339d62ced9118f1c4caeeec4ae978e7d86596a1d1cc52276ea65',
     'wad': 'b1d0fc43d987eee9e1dfee0e6bdecde8cf1ce5b15b9a09f79751bd73c553f3d8',
     'stats': ('KILLCOUNT', 'HEALTH', 'AMMO2')},
    'take-cover': {'stem': 'take_cover',
     'goal': None,
     'start_tic': 1,
     'timeout_tics': 0,
     'buttons': ['MOVE_LEFT', 'MOVE_RIGHT'],
     'cfg': '9dd89baabf83eac8dfa8dc37afffbd5a94c653e9de196b4086eeb9605c62eab2',
     'wad': '6fcd3c50c7f303628a9c36f1af68dd5b683c56a81302cd1118f569dbb6637990',
     'stats': ('HEALTH',)},
    'health-gathering': {'stem': 'health_gathering',
     'goal': None,
     'start_tic': 1,
     'timeout_tics': 2100,
     'buttons': ['TURN_LEFT', 'TURN_RIGHT', 'MOVE_FORWARD'],
     'cfg': '582a547f47e7a721a8728d30690d018d7588644074c7a204cd9e401f63090e2e',
     'wad': 'c77c8ba3254ae19eaff8d00418870a7718ef8a5822e5872ab68b76205cb2bacf',
     'stats': ('HEALTH', 'ITEMCOUNT')},
    'health-gathering-supreme': {'stem': 'health_gathering_supreme',
     'goal': None,
     'start_tic': 1,
     'timeout_tics': 2100,
     'buttons': ['TURN_LEFT', 'TURN_RIGHT', 'MOVE_FORWARD'],
     'cfg': 'd53069631aacb542bd9bf5349787f5d4f5bf61a9f720cd23ae9cc3d89d2f4fe7',
     'wad': 'dade758e5295adfd860721cb9d5ac42576a560b1283bf572bf656a056fda3515',
     'stats': ('HEALTH', 'ITEMCOUNT')},
    'deathmatch': {'stem': 'deathmatch',
     'goal': None,
     'start_tic': 1,
     'timeout_tics': 4200,
     'buttons': ['ATTACK',
                 'SPEED',
                 'STRAFE',
                 'MOVE_RIGHT',
                 'MOVE_LEFT',
                 'MOVE_BACKWARD',
                 'MOVE_FORWARD',
                 'TURN_RIGHT',
                 'TURN_LEFT',
                 'SELECT_WEAPON1',
                 'SELECT_WEAPON2',
                 'SELECT_WEAPON3',
                 'SELECT_WEAPON4',
                 'SELECT_WEAPON5',
                 'SELECT_WEAPON6',
                 'SELECT_NEXT_WEAPON',
                 'SELECT_PREV_WEAPON',
                 'LOOK_UP_DOWN_DELTA',
                 'TURN_LEFT_RIGHT_DELTA',
                 'MOVE_LEFT_RIGHT_DELTA'],
     'cfg': 'ab2b1a71fecda7e156d43e015aec4e48a5141795c0c22777f654ea00ee75c407',
     'wad': '1d06c2113f2c1546062635ad599f49cd852287a08b7b07b26d30b8f4c362a42d',
     'stats': ('KILLCOUNT', 'HEALTH', 'ARMOR', 'SELECTED_WEAPON', 'SELECTED_WEAPON_AMMO')},
}


def scenario_hashes(family):
    scene = SCENARIOS[family]
    return {**COMMON_ASSETS, **{f"scenarios/{scene['stem']}.{ext}": scene[ext] for ext in ("cfg", "wad")}}


def validate(instance):
    family = instance["family"]
    if family not in SCENARIOS:
        raise ValueError("unsupported ViZDoom scenario")
    scene = SCENARIOS[family]
    validate_engine_versions(instance["engine_versions"], ENGINE_VERSIONS)
    if (instance["engine_commit"] != ENGINE_COMMIT or
            instance["scenario_hashes"] != scenario_hashes(family)):
        raise ValueError("unsupported ViZDoom engine or scenario assets")
    default_tics = instance["tics_per_decision"]
    if type(default_tics) is not int or default_tics not in (1, 4):
        raise ValueError("unsupported ViZDoom tic profile")
    if (instance["env_id"] != f"ViZDoom/{scene['stem']}" or
            instance["buttons"] != scene["buttons"] or instance["max_steps"] is not None or
            any(type(instance[k]) is not int or instance[k] != scene[k] for k in ("start_tic", "timeout_tics"))):
        raise ValueError("unsupported ViZDoom buttons or native timing")
    if default_tics == 4 and family not in {"basic", "my-way-home"}:
        raise ValueError("only the two historical ViZDoom tasks support fixed tics")
    if instance["observation_profile"] != scene.get("observation_profile", "rgb-first-person-v1"):
        raise ValueError("unsupported ViZDoom observation profile for this scenario")
    expected_metric = "objective_success" if scene["goal"] else "native_return"
    if instance["metric_spec"]["primary"] != expected_metric:
        raise ValueError("unsupported ViZDoom metric for this scenario")
    action_mode = "text" if default_tics == 1 else "enum"
    if instance["capabilities"] != {"images": True, "action_mode": action_mode, "timing": "action-stepped",
                                    "native_truncation": True}:
        raise ValueError("unsupported ViZDoom player profile")
