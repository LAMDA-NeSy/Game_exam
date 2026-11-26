#!/bin/sh
# Offline probe using the native inventory API and a per-trial REPL variable.
set -eu
test ! -e /evidence
test ! -e /native/fle_bridge.sock
test ! -e /tmp/fle-collect.sock
test ! -e /var/run/docker.sock
python /opt/fle_client.py prompt >/dev/null
python /opt/fle_client.py observe >/dev/null
marker=$(python -c 'import uuid; print(uuid.uuid4().hex)')
printf "trial_marker = '%s'\nprint(inspect_inventory())\n" "$marker" > /tmp/check_inventory.py
python /opt/fle_client.py step 1 /tmp/check_inventory.py > /tmp/step.json
python -c 'import json; r=json.load(open("/tmp/step.json")); assert r["next_step"] == 2 and not r["error_occurred"] and r["reward"] == 0'
echo 'print(trial_marker)' | python /opt/fle_client.py step 2 - > /tmp/readback.json
python -c 'import json,sys; r=json.load(open("/tmp/readback.json")); assert not r["error_occurred"] and sys.argv[1] in r["result"]' "$marker"
mkdir -p /logs/artifacts
printf '%s\n' "$marker" > /logs/artifacts/fle-probe-id
