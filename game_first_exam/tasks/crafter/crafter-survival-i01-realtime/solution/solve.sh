#!/bin/bash
set -euo pipefail
python3 - <<'PYCODE'
import json,time
from realtime_client import GameClient
client=GameClient()
actions=json.load(open('/solution/actions.json'))
result=client.submit(actions)
target=result['plan_end_step']
while True:
    status=client.status()
    if status['done'] or status['step']>=target:break
    time.sleep(.05)
print('Reference plan executed',status)
PYCODE
