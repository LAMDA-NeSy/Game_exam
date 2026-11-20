"""Read-only preflight: reject malformed suites and inconsistent frozen task assembly before Docker/Harbor."""
import hashlib
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'game_first_exam/runtime'))
import files_image
import task_conventions as tc
from config_schema import PROTOCOL, positive, validate_instance, validate_suite
from game_schemas import load_schema, metric_scope, register_schemas, schema_paths
sys.path.insert(0, str(ROOT / 'game_first_exam/runtime/modes'))
from mode_config import validate_mode


def validate_task(row, task_path=None):
    schema = load_schema(row['benchmark'])
    task = Path(task_path) if task_path is not None else tc.task_dir(row['name'])
    config = tomllib.loads((task / 'task.toml').read_text())
    instance = json.loads((task / 'tests/instance.json').read_text())
    validate_instance(instance)
    if json.loads((task / 'environment/sim/instance.json').read_text()) != instance:
        raise ValueError(f'{task.name}: simulator/verifier instances differ')
    if (instance['benchmark'], instance['family']) != (row['benchmark'], row['family']):
        raise ValueError(f'{task.name}: suite and instance disagree')
    mode = tc.mode_of(task)
    expected_protocol = {'standard': PROTOCOL, 'realtime': 'game-realtime/1.0', 'privileged': None}[mode]
    if config['metadata'].get('protocol') != expected_protocol or config['metadata']['instance_seed'] != instance['seed']:
        raise ValueError(f'{task.name}: task metadata differs from instance')
    positive(config['agent']['timeout_sec'], 'agent timeout')
    for field in ('cpus', 'memory_mb', 'storage_mb'):
        positive(config['environment'][field], field)
    for name, expected in instance.get('asset_sha256', {}).items():
        if hashlib.sha256((task / 'environment/sim' / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'{task.name}: asset mismatch: {name}')
    paths = {
        'environment/Dockerfile': {
            '/app/game_client.py': ROOT / 'game_first_exam/runtime/game_client.py',
            '/app/service_connection.py': ROOT / 'shared/connection/service_connection.py'},
        'environment/sim/Dockerfile': {f'/srv/{name}.py': ROOT / f'game_first_exam/runtime/{name}.py'
            for name in ('server', 'contracts', 'config_schema', 'reducers', 'encoding', 'recording')},
        'tests/Dockerfile': {f'/tests/{name}.py': ROOT / f'game_first_exam/runtime/{name}.py'
            for name in ('grade', 'config_schema', 'reducers')},
    }
    client = getattr(schema, 'STANDARD_CLIENT', None) if mode == 'standard' else None
    if client:
        agent_paths = paths['environment/Dockerfile']
        agent_paths['/app/standard_game_client.py'] = agent_paths['/app/game_client.py']
        agent_paths['/app/game_client.py'] = schema_paths()[row['benchmark']].with_name(client)
    if client:
        bench_root = schema_paths()[row['benchmark']].parent
        paths['environment/Dockerfile']['/app/vizdoom_actions.py'] = bench_root / 'vizdoom_actions.py'
        paths['environment/sim/Dockerfile']['/srv/vizdoom_actions.py'] = bench_root / 'vizdoom_actions.py'
        paths['environment/sim/Dockerfile']['/srv/vizdoom_server.py'] = bench_root / 'vizdoom_server.py'
    paths['environment/sim/Dockerfile']['/srv/adapter.py'] = ROOT / f"game_first_exam/benchmarks/{row['benchmark']}/adapter.py"
    paths['tests/Dockerfile']['/tests/metric_rules.py'] = ROOT / f"game_first_exam/benchmarks/{row['benchmark']}/metric_rules.py"
    for file, prefix in [('environment/sim/Dockerfile', '/srv'), ('tests/Dockerfile', '/tests')]:
        paths[file][prefix + '/instance_schema.py'] = schema_paths()[row['benchmark']]
    if mode != 'standard':
        mode_config = validate_mode(json.loads((task / 'tests/mode.json').read_text()))
        if mode_config['mode'] != mode:
            raise ValueError('task mode and execution settings differ')
        location = 'environment/mode.json' if mode == 'privileged' else 'environment/sim/mode.json'
        if json.loads((task / location).read_text()) != mode_config:
            raise ValueError('execution settings differ between runtime and verifier')
        modes_root = ROOT / 'game_first_exam/runtime/modes'
        paths['tests/Dockerfile']['/tests/mode_grade.py'] = modes_root / 'mode_grade.py'
        paths['tests/Dockerfile']['/tests/mode_config.py'] = modes_root / 'mode_config.py'
        if mode == 'privileged':
            if mode_config['max_actions'] != instance['native_max_steps']:
                raise ValueError('replay limit must equal the native limit')
            paths.pop('environment/sim/Dockerfile')
            paths['environment/Dockerfile'] = {
                '/app/privileged.py': modes_root / 'privileged.py',
                '/srv/adapter.py': ROOT / f"game_first_exam/benchmarks/{row['benchmark']}/adapter.py",
                '/srv/instance_schema.py': schema_paths()[row['benchmark']],
            }
            paths['tests/Dockerfile']['/srv/adapter.py'] = ROOT / f"game_first_exam/benchmarks/{row['benchmark']}/adapter.py"
        else:
            paths['environment/Dockerfile']['/app/realtime_client.py'] = modes_root / 'realtime_client.py'
            paths['environment/sim/Dockerfile']['/srv/realtime_server.py'] = modes_root / 'realtime_server.py'
            paths['environment/sim/Dockerfile']['/srv/mode_config.py'] = modes_root / 'mode_config.py'
    for file, expected in paths.items():
        copied, errors = files_image.copied_from(task / file)
        if errors or any(copied.get(target) != source for target, source in expected.items()):
            raise ValueError(f'{task.name}: missing/stale public service binding in {file}: {errors}')
    collectors = config['verifier']['collect']
    services = [item['service'] for item in collectors]
    expected_services = {'privileged': ['rcb_monitor', 'main'], 'realtime': ['sim', 'rcb_monitor', 'main'], 'standard': ['rcb_monitor', 'main', 'sim']}[mode]
    sim_hook = next((item for item in collectors if item['service'] == 'sim'), None)
    if services != expected_services or (mode != 'privileged' and ('-USR1' not in sim_hook['command'] or 'collection.ready' not in sim_hook['command'])):
        raise ValueError(f'{task.name}: invalid collection order for {mode}')
    if config['verifier']['environment_mode'] != 'separate' or config['verifier']['network_mode'] != 'no-network':
        raise ValueError(f'{task.name}: verifier isolation is required')
    if (task / 'DIGEST').read_text().strip() != tc.digest(task):
        raise ValueError(f'{task.name}: stale task digest; normalize before running')
    return task, config, instance


def preflight(suite):
    register_schemas()
    validate_suite(suite)
    for name in suite['files_images']:
        manifest, _ = files_image.oci(name)
        if files_image.image(name).split('@')[-1] != 'sha256:' + hashlib.sha256(manifest).hexdigest():
            raise ValueError(f'{name}: stale files image digest')
    # Validate the whole named suite, including tasks excluded by a CLI filter.
    plans = {row['name']: validate_task(row) for row in suite['tasks']}
    metrics = {}
    for task, _, instance in plans.values():
        previous = metrics.setdefault(metric_scope(instance), instance['metric_spec'])
        if previous != instance['metric_spec']:
            raise ValueError(f'{task.name}: incompatible metric definitions within benchmark')
    known_images = {p.parent.name: files_image.image(p.parent.name) for p in files_image.manifests()}
    used = set()
    for task, _, _ in plans.values():
        for df in task.rglob('Dockerfile'):
            for name, reference in known_images.items():
                if reference in df.read_text():
                    used.add(name)
    if used != set(suite['files_images']):
        raise ValueError('suite files_images differs from the images required by its tasks')
    return plans
