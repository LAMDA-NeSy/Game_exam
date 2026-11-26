#!/bin/sh
# Offline integration probe using one real FLE action.
set -eu
test ! -e /evidence
test ! -e /native/fle_bridge.sock
test ! -e /var/run/docker.sock
python /opt/fle_client.py prompt >/dev/null
python /opt/fle_client.py observe >/dev/null
echo 'print(inspect_inventory())' > /tmp/check_inventory.py
python /opt/fle_client.py step 1 /tmp/check_inventory.py > /tmp/step.json
python -c 'import json; r=json.load(open("/tmp/step.json")); assert r["next_step"] == 2 and not r["error_occurred"] and r["reward"] == 0'
