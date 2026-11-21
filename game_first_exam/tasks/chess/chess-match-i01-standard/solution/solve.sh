#!/bin/bash
set -euo pipefail
python3 - <<'PYCODE'
import json
from pathlib import Path

from game_client import GameClient

game = GameClient()
state = game.observe()
moves = json.loads(Path("/solution/white_moves.json").read_text())
for uci in moves:
    assert not state["done"], "reference match ended early"
    action = next(key for key, move in state["observation"]["legal_moves"].items() if move == uci)
    state = game.step(action, expected_step=state["step"])
assert state["done"] and state["observation"]["outcome"] == "win", "expected a native white win"
print("Native white win after", state["step"], "decisions and",
      len(state["observation"]["move_history_uci"]), "plies")
PYCODE
