"""Serialization helpers for adapters; these do not choose what the agent may see."""
import base64
import hashlib
import io
import json

from PIL import Image


def png(frame):
    stream = io.BytesIO()
    Image.fromarray(frame).save(stream, format="PNG")
    return base64.b64encode(stream.getvalue()).decode()


def state_hash(value):
    def default(obj):
        if isinstance(obj, (set, frozenset)):
            # Rules may contain sets (e.g. color predicates); iteration order is not state.
            items = sorted(obj, key=lambda value: json.dumps(value, default=default, sort_keys=True,
                                                             separators=(',', ':'), allow_nan=False))
            return {'__state_collection__': type(obj).__name__, 'items': items}
        if isinstance(obj, bytes):
            return {"bytes_sha256": hashlib.sha256(obj).hexdigest()}
        if hasattr(obj, "tolist"):
            return obj.tolist()
        if hasattr(obj, "item"):
            return obj.item()
        raise TypeError(type(obj).__name__)
    return hashlib.sha256(json.dumps(value, default=default, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()
