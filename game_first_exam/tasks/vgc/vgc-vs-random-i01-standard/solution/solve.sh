#!/bin/bash
set -euo pipefail
python3 - <<'PYCODE'
import json
from game_client import GameClient
client = GameClient()
obs = client.observe()
for action in json.load(open("/solution/actions.json")):
    if obs["done"]:
        break
    obs = client.step(action, obs["step"])
print("Reference episode finished at step", obs["step"], "done", obs["done"])
PYCODE
