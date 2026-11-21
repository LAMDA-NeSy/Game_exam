#!/bin/bash
rm -rf /logs/verifier/*   # verdicts from an earlier run never survive (docs/protocol/README.md Appendix H.1)
trap 'p=$(command -v python3 || command -v python); "$p" /tests/rcb_limits.py verify' EXIT   # resources, after the grader (PROTOCOL §6)
p=$(command -v python3 || command -v python); "$p" /tests/rcb_limits.py sanitize /app/output || true   # untrusted agent files (PROTOCOL H.1)
set -eu
mkdir -p /logs/verifier
CHESS_VERIFY_TRACE=/data/chess_plies.jsonl python3 /tests/grade.py 2>/logs/verifier/grade.log
