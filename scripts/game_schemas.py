"""Explicit trusted host registry; runtime tasks instead contain one frozen sibling schema."""
import hashlib
import importlib.util
import tomllib
from functools import cache
from pathlib import Path, PurePosixPath

from config_schema import register_instance_schema

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'configs/game_benchmarks.toml'


def _trusted_source(source):
    if not isinstance(source, str):
        raise ValueError('invalid trusted benchmark source')
    relative = PurePosixPath(source)
    if relative.is_absolute() or '..' in relative.parts or str(relative) != source:
        raise ValueError('source outside trusted benchmark sources')
    path = (ROOT / source).resolve()
    if not path.is_relative_to(ROOT / 'game_first_exam/benchmarks'):
        raise ValueError('source outside trusted benchmark sources')
    return path


def registrations():
    """Read only the host registry; instances cannot nominate runtime code or source paths."""
    registered = tomllib.loads(REGISTRY.read_text())
    if set(registered) != {'benchmarks'} or not isinstance(registered['benchmarks'], dict):
        raise ValueError('invalid trusted game registry')
    result = {}
    for name, row in registered['benchmarks'].items():
        if (not isinstance(row, dict) or 'schema' not in row
                or set(row) - {'schema', 'adapter', 'metric_rules', 'runtime_files'}):
            raise ValueError('invalid game schema registration')
        path = _trusted_source(row['schema'])
        if path.name != 'instance_schema.py':
            raise ValueError('schema outside trusted benchmark sources')
        runtime = row.get('runtime_files', {})
        if not isinstance(runtime, dict):
            raise ValueError('invalid trusted runtime files')
        files = {}
        for target, source in runtime.items():
            destination = PurePosixPath(target)
            if (not destination.is_relative_to('/srv') or destination == PurePosixPath('/srv')
                    or '..' in destination.parts or str(destination) != target):
                raise ValueError('runtime target outside trusted service directory')
            files[target] = _trusted_source(source)
        sources = {'schema': path}
        for kind in ('adapter', 'metric_rules'):
            source = _trusted_source(row.get(kind, f'game_first_exam/benchmarks/{name}/{kind}.py'))
            if source.name != kind + '.py':
                raise ValueError('invalid trusted benchmark ' + kind)
            sources[kind] = source
        result[name] = {**sources, 'runtime_files': files}
    return result


def schema_paths():
    return {name: row['schema'] for name, row in registrations().items()}


def runtime_files(name):
    rows = registrations()
    if name not in rows:
        raise ValueError('unregistered benchmark: ' + str(name))
    return rows[name]['runtime_files']


def benchmark_paths(name):
    rows = registrations()
    if name not in rows:
        raise ValueError('unregistered benchmark: ' + str(name))
    return {key: rows[name][key] for key in ('schema', 'adapter', 'metric_rules')}


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
