"""Deterministic selection from the native legal action map."""
import hashlib
import json


def choose(legal, seed, history):
    ordered = sorted(legal, key=legal.__getitem__)
    key = json.dumps([seed, len(history), history], separators=(',', ':')).encode()
    index = int.from_bytes(hashlib.sha256(key).digest(), 'big') % len(ordered)
    return ordered[index]
