#!/bin/bash
set -euo pipefail
/app/minihack_python - <<'PYCODE'
import json
from privileged import Session
session=Session()
for action in json.load(open('/solution/actions.json')):
    session.step(action)
session.save()
session.close()
PYCODE
