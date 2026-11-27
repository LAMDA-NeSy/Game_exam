#!/bin/bash
set -euo pipefail
cp /solution/control.py /app/output/gen.py
python3 /app/output/gen.py
