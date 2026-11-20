#!/bin/bash
set -euo pipefail
python3 - <<'PYCODE'
import json
from game_client import GameClient

client = GameClient()
obs = client.observe()
for action, tics, *continuous in json.load(open("/solution/actions.json")):
    if obs["done"]:
        break
    controls = {"deltas": continuous[0]} if continuous else {}
    obs = client.step(action, obs["step"], tics=tics, **controls)
print("Reference executed", obs["step"], "decisions")
PYCODE
