"""Whitelisted host/runtime provenance. Never record container environment or credentials."""
import ast
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER_VERSION = 'game-harbor/1.2.0'


def command(argv):
    return subprocess.check_output(argv, text=True, stderr=subprocess.DEVNULL, timeout=10).strip()


def report_code_metadata():
    # Hash the conservative local import closure, including imports inside functions.
    # This includes account_failure_check/retry_policy, which can change the denominator.
    roots = [ROOT / 'scripts', ROOT / 'game_first_exam/runtime', ROOT / 'images/monitor']
    pending = [ROOT / 'scripts' / name for name in
               ('efe.py', 'run_games.py', 'game_reports.py', 'game_harbor.py', 'prepare_games.py')]
    files = set()
    while pending:
        path = pending.pop()
        if path in files:
            continue
        files.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            search = roots
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ''
                names = [base] + [f'{base}.{a.name}'.strip('.') for a in node.names if a.name != '*']
                if node.level:
                    search = [path.parents[node.level - 1]]
            for name in names:
                if not name:
                    continue
                parts = name.split('.')
                for root in search:
                    for candidate in (root.joinpath(*parts).with_suffix('.py'), root.joinpath(*parts, '__init__.py')):
                        if candidate.is_file():
                            pending.append(candidate)
                    for i in range(1, len(parts)):
                        init = root.joinpath(*parts[:i], '__init__.py')
                        if init.is_file():
                            pending.append(init)
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def frozen_instance_metadata(instance):
    # JSON round-trip freezes a detached, complete instance; no per-game field selection.
    encoded = json.dumps(instance, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return {'instance': json.loads(encoded), 'instance_sha256': hashlib.sha256(encoded.encode()).hexdigest()}


def validate_report_code(snapshot):
    if snapshot.get('report_code_sha256') != report_code_metadata():
        raise ValueError('report implementation differs from the frozen run (or is unversioned); use the recorded checkout')


def runner_metadata():
    enforce = os.environ.get('RCB_LIMITS_ENFORCE', '0')
    if enforce not in {'0', '1'}:
        raise ValueError('RCB_LIMITS_ENFORCE must be 0 or 1')
    sources = [ROOT / 'scripts' / f for f in
               ('game_harbor.py', 'game_reports.py', 'prepare_games.py', 'game_preflight.py', 'game_runtime.py')]
    sources += sorted((ROOT / 'game_first_exam/runtime').glob('*.py'))
    return {'version': RUNNER_VERSION, 'harbor_version': importlib.metadata.version('harbor'),
            'python_version': platform.python_version(), 'host_platform': platform.platform(),
            'git_commit': command(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']),
            'git_dirty': bool(command(['git', '-C', str(ROOT), 'status', '--porcelain'])),
            'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            'docker_server': json.loads(command(['docker', 'version', '--format', '{{json .Server}}'])),
            'resource_enforcement_requested': int(enforce),
            'interaction_policy': {'automatic_attempt_retries': 0, 'token_budget': None,
                                   'tool_call_budget': None, 'monetary_budget': None,
                                   'model_cost_source': 'Harbor agent_result; null means unavailable'}}


def project_trial(project, trials):
    for trial in trials:
        if project in {trial.lower() + '__env', trial.lower() + '__verifier__trial'}:
            return trial
    return None


class RuntimeCapture:
    """Observe only this job's Compose projects while Harbor still owns the containers."""
    def __init__(self, job):
        self.job = Path(job)
        self.records = {}
        self.errors = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        self.thread.start()

    def sample(self):
        if not self.job.exists():
            return
        trials = [p.name for p in self.job.iterdir() if p.is_dir() and (p / 'config.json').exists()]
        lines = command(['docker', 'ps', '--no-trunc', '--format', '{{json .}}'])
        for line in lines.splitlines():
            if self.stop.is_set():
                break
            item = json.loads(line)
            labels = dict(pair.split('=', 1) for pair in item.get('Labels', '').split(',') if '=' in pair)
            project = labels.get('com.docker.compose.project', '')
            trial = project_trial(project, trials)
            if not trial or item['ID'] in self.records:
                continue
            # Do not inspect .Config.Env, command arguments, mounts, or authentication files.
            fmt = '[{{json .Id}},{{json .Image}},{{json .Config.Image}},{{json .HostConfig.Memory}},{{json .HostConfig.NanoCpus}},{{json .HostConfig.PidsLimit}}]'
            values = json.loads(command(['docker', 'inspect', '--format', fmt, item['ID']]))
            image = json.loads(command(['docker', 'image', 'inspect', '--format',
                                       '[{{json .RepoDigests}},{{json .Os}},{{json .Architecture}}]', values[1]]))
            self.records[item['ID']] = {'trial': trial, 'project': project,
                'service': labels.get('com.docker.compose.service'), 'container_id': values[0],
                'image_id': values[1], 'configured_image': values[2], 'repo_digests': image[0] or [],
                'os': image[1], 'architecture': image[2], 'memory_bytes': values[3],
                'nano_cpus': values[4], 'pids_limit': values[5]}

    def run(self):
        while not self.stop.is_set():
            try:
                self.sample()
            except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
                self.errors.append(type(exc).__name__)
            self.stop.wait(.5)

    def finish(self):
        self.stop.set()
        self.thread.join(timeout=35)
        trials = [p.name for p in self.job.iterdir() if p.is_dir() and (p / 'config.json').exists()]
        coverage = {}
        for trial in trials:
            selected = [r for r in self.records.values() if r['trial'] == trial]
            lock_path = self.job / trial / 'lock.json'
            lock = json.loads(lock_path.read_text()) if lock_path.exists() else {}
            from task_conventions import mode_of
            mode = mode_of(Path(lock.get('task', {}).get('name', 'unknown-standard')))
            services = ('main', 'rcb_monitor') if mode == 'privileged' else ('main', 'sim', 'rcb_monitor')
            expected = {(trial.lower() + '__env', s) for s in services}
            expected.add((trial.lower() + '__verifier__trial', 'main'))
            missing = expected - {(r['project'], r['service']) for r in selected}
            coverage[trial] = {'complete': not missing, 'missing_roles': sorted(missing)}
        result = {'schema': 'game-runtime-images/1.0', 'containers': list(self.records.values()),
                  'coverage': coverage, 'capture_errors': self.errors,
                  'complete': bool(coverage) and all(r['complete'] for r in coverage.values()) and not self.thread.is_alive()}
        (self.job / 'runtime-images.json').write_text(json.dumps(result, indent=2) + '\n')
        return {'artifact': 'runtime-images.json', 'sha256': hashlib.sha256((self.job / 'runtime-images.json').read_bytes()).hexdigest(),
                'complete': result['complete'], 'container_count': len(result['containers'])}
