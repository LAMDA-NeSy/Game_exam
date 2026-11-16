"""Trusted, stdlib-only game configuration; shared by preflight, sim and verifier."""
from config_schema import validate_engine_versions

SCHEMA_VERSION = '1.0.0'
BENCHMARK = 'minigrid'
FIELDS = {'minigrid_version', 'gymnasium_version', 'native_max_steps'}
METRICS = {'success', 'native_return'}
PROFILES = {'native-observation-v1'}
REDUCERS = {('family_macro', '1.0.0')}


def validate(value):
    validate_engine_versions({k: value[k] for k in ('minigrid_version', 'gymnasium_version')},
                             {'minigrid_version': '3.2.0', 'gymnasium_version': '1.4.0'})
    limits = {'MiniGrid-DoorKey-8x8-v0': 640, 'MiniGrid-Dynamic-Obstacles-8x8-v0': 256,
              'MiniGrid-Empty-Random-6x6-v0': 144, 'MiniGrid-LavaCrossingS9N1-v0': 324,
              'MiniGrid-MemoryS11-v0': 605, 'MiniGrid-MultiRoom-N4-S5-v1': 80}
    if value['env_id'] not in limits or type(value['native_max_steps']) is not int or value['native_max_steps'] != limits[value['env_id']]:
        raise ValueError('native MiniGrid configuration mismatch')
