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
for path in jobs[-2:]:
    stats = json.loads(path.read_text())['stats']
    print(path, 'completed', stats['n_completed_trials'], 'errors', stats['n_errored_trials'])
    for name, report in stats.get('evals', {}).items():
        for metric in report.get('metrics', []):
            print(name, {key: metric.get(key) for key in ('environment_error', 'primary_score')})
PY
