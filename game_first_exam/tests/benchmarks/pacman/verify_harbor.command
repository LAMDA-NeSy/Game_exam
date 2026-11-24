#!/bin/bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/../../../.." && pwd)"
base="$(cd "$repo/../Game_exam-main" && pwd)"
export PATH="$base/.venv/bin:/Applications/Docker.app/Contents/Resources/bin:$PATH"
export DOCKER_HOST="unix://$HOME/.docker/run/docker.sock"
export EFE_ROOT="$repo"
cd "$repo"

docker info --format 'Docker server: {{.ServerVersion}}'
python scripts/files_image.py build pacman-files
harbor run --game-suite pacman --standard -a oracle -y
python game_first_exam/tests/benchmarks/pacman/ghost_collision/run_harbor.py

python - <<'PY'
import json
from pathlib import Path

jobs = sorted(Path('jobs').glob('20*/result.json'), key=lambda p: p.stat().st_mtime)
if len(jobs) < 2:
    raise SystemExit('Both Harbor jobs must write a result.json')
scores = []
for path in jobs[-2:]:
    stats = json.loads(path.read_text())['stats']
    print(path, 'completed', stats['n_completed_trials'], 'errors', stats['n_errored_trials'])
    if stats['n_completed_trials'] != 1 or stats['n_errored_trials']:
        raise SystemExit('Harbor failed before grading; inspect the trial result.json')
    for name, report in stats.get('evals', {}).items():
        for metric in report.get('metrics', []):
            print(name, {key: metric.get(key) for key in ('environment_error', 'primary_score')})
            scores.append(metric.get('primary_score'))
if scores != [1.0, 0.0]:
    raise SystemExit(f'Expected success and failure scores [1.0, 0.0], got {scores}')
print('PASS: Oracle clear and failure control were graded separately')
PY
