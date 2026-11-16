#!/bin/bash
set -euo pipefail
python3 - <<'PYCODE'
import json
from game_client import GameClient
client=GameClient()
obs=client.observe()
for action in json.load(open("/solution/actions.json")):
    if obs["done"]: break
    obs=client.step(action,obs["step"])
# Native Crafter has no global win. Ending the reference program seals its achieved milestones.
print("Reference episode completed in",obs["step"],"steps")
PYCODE
