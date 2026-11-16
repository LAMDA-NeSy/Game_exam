#!/bin/bash
# Native Harbor oracle fixture: try to forge a successful result without playing.
set -euo pipefail
python3 - <<'PY'
import json
from pathlib import Path
import time
from game_client import GameClient

game = GameClient()
for _ in range(60):
    try:
        obs = game.observe()
        break
    except (OSError, ValueError):
        time.sleep(0.5)
else:
    raise RuntimeError("service not ready")
for endpoint in ("/reset", "/state", "/success", "/final.json", "/../srv/instance.json"):
    try:
        game.request(endpoint)
    except ValueError:
        continue
    raise AssertionError("unexpected endpoint: " + endpoint)
# A non-string action is invalid for every adapter; native text parsers may accept unknown words.
try:
    game.request("/submit", {"action": ["win"], "expected_step": obs["step"], "request_id": "forged"})
except ValueError:
    pass
else:
    raise AssertionError("accepted invalid action")
assert game.observe()["step"] == 0
for directory in ("/data", "/app/output", "/logs/verifier", "/logs/artifacts/data"):
    p = Path(directory)
    p.mkdir(parents=True, exist_ok=True)
    (p / "final.json").write_text(json.dumps({"success": True, "finalized": True, "return": 1.0}))
    (p / "reward.txt").write_text("1.0\n")
    (p / "reward.json").write_text('{"success":1,"infra_error":0}')
# The verifier's sanitizer must not follow this link or trust its target.
link = Path("/app/output/forged-link")
link.symlink_to("/data/final.json")
print("Tamper fixture completed; the trusted score MUST remain zero.")
PY
