#!/bin/bash
set -euo pipefail
repo="$(cd "$(dirname "$0")/../../../.." && pwd)"
if [ ! -x "$repo/.venv/bin/python" ]; then
    python3 -m venv "$repo/.venv"
fi
python="$repo/.venv/bin/python"
"$python" -m pip install -q -r "$repo/game_first_exam/benchmarks/pacman/requirements.txt"
"$python" -m playwright install chromium --only-shell
"$python" "$repo/game_first_exam/tests/benchmarks/pacman/native_probe.py"
"$python" "$repo/game_first_exam/tests/benchmarks/pacman/calibrate.py"
