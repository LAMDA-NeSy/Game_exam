"""Explicit trusted host registry; runtime tasks instead contain one frozen sibling schema."""
import hashlib
import importlib.util
import tomllib
from functools import cache
from pathlib import Path

from config_schema import register_instance_schema

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'configs/game_benchmarks.toml'


def schema_paths():
    registered = tomllib.loads(REGISTRY.read_text())
    if set(registered) != {'benchmarks'}:
        raise ValueError('invalid trusted game registry')
    result = {}
    for name, row in registered['benchmarks'].items():
        if set(row) != {'schema'} or not isinstance(row['schema'], str):
            raise ValueError('invalid game schema registration')
        path = (ROOT / row['schema']).resolve()
        if not path.is_relative_to(ROOT / 'game_first_exam/benchmarks') or path.name != 'instance_schema.py':
            raise ValueError('schema outside trusted benchmark sources')
        result[name] = path
    return result


@cache
def load_schema(name):
    paths = schema_paths()
    if name not in paths:
        raise ValueError('unregistered benchmark: ' + str(name))
    spec = importlib.util.spec_from_file_location('_game_schema_' + name, paths[name])
    schema = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(schema)
    if schema.BENCHMARK != name:
        raise ValueError('registry and schema benchmark disagree')
    return register_instance_schema(schema)


def register_schemas():
    for name in schema_paths():
        load_schema(name)


def schema_metadata(name):
    schema = load_schema(name)
    path = schema_paths()[name]
    return {'contract_version': schema.SCHEMA_VERSION, 'source': str(path.relative_to(ROOT)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def is_scenario_score(record):
    """Native scores declared by the benchmark are comparable within the scenario."""
    metric = record["metric_spec"]["primary"]
    if metric != "native_return":
        return False
    schema = load_schema(record["benchmark"])
    return metric in getattr(schema, "PER_SCENARIO_METRICS", ())


def metric_scope(record):
    family = record["family"] if is_scenario_score(record) else None
    return record["benchmark"], family
