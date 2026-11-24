#!/usr/bin/env bash
# Run both reference outcomes on a host with Docker Desktop and Harbor installed.
set -euo pipefail
root="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$root"

# Reuse the adjacent development virtualenv when invoked from this checkout.
if [ -x ../Game_exam-main/.venv/bin/harbor ]; then
  export PATH="$(cd ../Game_exam-main/.venv/bin && pwd):$PATH"
fi
export PATH="/Applications/Docker.app/Contents/Resources/bin:$HOME/.docker/bin:$PATH"
export DOCKER_HOST="unix://$HOME/.docker/run/docker.sock"

docker info --format 'Docker server: {{.ServerVersion}}'
harbor run --game-suite connectfour --standard \
  -c configs/harbor/oracle.json --plugin game_harbor:GameRecords \
  --jobs-dir "$PWD/jobs" --job-name connectfour-win -y
python game_first_exam/tests/benchmarks/connectfour/loss/run_harbor.py
python ci_checks/check-connectfour-result.py jobs/connectfour-win jobs/connectfour-loss
