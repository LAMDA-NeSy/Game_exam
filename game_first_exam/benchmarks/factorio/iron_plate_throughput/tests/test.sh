#!/bin/sh
set -eu
test ! -e /channel/game.sock
test ! -e /native/fle_bridge.sock
test ! -e /tmp/fle-collect.sock
test ! -e /var/run/docker.sock
exec /opt/fle-venv/bin/python /tests/grade.py
