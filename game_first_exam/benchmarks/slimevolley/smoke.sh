#!/bin/bash
set -eu
python3 - <<'PY'
from game_client import GameClient

game = GameClient()

def frames(state):
    result = []
    for _ in range(100):
        state = game.step("idle", state["step"])
        result.append(state["observation"]["image_png_base64"])
    return result

first = frames(game.observe())
second = frames(game.request("/practice/start", {"slot": "B"}))
assert first != second, "the seeds must yield different practice trajectories"
assert first == frames(game.request("/practice/start", {"slot": "A"})), "reset must reproduce the selected seed"
try:
    game.request("/practice/start", {"slot": "official"})
except ValueError as error:
    assert "provide exactly one slot" in str(error), str(error)
else:
    raise AssertionError("the practice reset accepted an unknown slot")
PY
mkdir -p /app/output
cat > /app/output/practice_gen.py <<'PY'
import os
from importlib.util import find_spec
from pathlib import Path
from shutil import which
from game_client import GameClient

assert find_spec("slimevolleygym") is None
assert which("codex") is None
assert not any(Path(name).exists() for name in (
    "/srv/instance.json", "/data/final.json", "/tests/grade.py", "/solution", "/var/run/docker.sock",
))
assert not any(name.endswith(("API_KEY", "AUTH_TOKEN")) for name in os.environ)
game = GameClient()
assert set(game.spec()) == {
    "action_schema", "adapter_version", "capabilities", "max_steps", "observation",
    "observation_profile", "protocol", "reset_budget", "timing",
}
try:
    game.request("/practice/start", {"slot": "A"})
except ValueError as error:
    assert "unknown endpoint" in str(error), str(error)
else:
    raise AssertionError("a reset was possible in the scored match")
state = game.observe()
assert state["step"] == 0
assert set(state["observation"]) == {"image_png_base64"}
assert game.step("left", state["step"])["step"] == 1
PY
sleep 60
