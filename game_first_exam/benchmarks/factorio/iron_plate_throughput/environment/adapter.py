"""Mediate one native FLE episode. The REPL runs only in the engine container."""
import hashlib
import json
import math
import os
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from fle_client import request

TASK = "iron_plate_throughput"
LIMIT = 64  # Checked against the upstream task in the verifier.


def native(command, payload=None):
    try:
        return request("/native/fle_bridge.sock", command, payload)
    except (ValueError, OSError) as error:
        raise RuntimeError(f"FLE bridge {command} failed: {error}") from error


class Episode:
    def __init__(self, call, evidence):
        self.call = call
        self.evidence = evidence
        self.steps = []
        self.last_reply = None
        self.sealed = False
        self.fault = None
        call("reset", {})
        self.prompt = call("system-prompt")["system_prompt"]
        self.initial = call("observe")
        self.save()

    def save(self):
        data = {"task": TASK, "sealed": self.sealed, "fault": self.fault, "steps": self.steps}
        tmp = self.evidence.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, allow_nan=False), encoding="utf-8")
        tmp.replace(self.evidence)

    def status(self):
        done = (self.sealed or self.fault is not None or len(self.steps) == LIMIT
                or bool(self.steps and (self.steps[-1]["terminated"] or self.steps[-1]["truncated"])))
        return {"steps": len(self.steps), "next_step": None if done else len(self.steps) + 1,
                "done": done, "fault": self.fault}

    def execute(self, number, code):
        if type(number) is not int or not isinstance(code, str):
            raise ValueError("Expected an integer step number and Python source text")
        digest = hashlib.sha256(code.encode()).hexdigest()
        if self.steps and number == len(self.steps) and digest == self.steps[-1]["code_sha256"]:
            return {**self.last_reply, **self.status()}
        if number != self.status()["next_step"]:
            raise ValueError("Episode closed or unexpected step number. Check status.")
        result = self.call("execute", {"agent_idx": 0, "code": code})
        step = {"number": number, "code_sha256": digest, "code": code}
        for key in ("reward", "production_score", "automated_production_score"):
            value = result[key]
            if type(value) not in (float, int) or not math.isfinite(value):
                raise RuntimeError(f"Invalid native {key}")
            step[key] = value
        for key in ("terminated", "truncated", "error_occurred"):
            if type(result[key]) is not bool:
                raise RuntimeError(f"Invalid native {key}")
            step[key] = result[key]
        self.steps.append(step)
        self.save()
        # Rollback snapshots are private to the upstream bridge.
        self.last_reply = {k: v for k, v in result.items() if k != "game_state_raw"}
        self.last_reply.update(self.status())
        return self.last_reply

    def dispatch(self, method, path, payload):
        if (method, path) == ("GET", "/status"):
            return self.status()
        if self.fault:
            raise RuntimeError(self.fault)
        if (method, path) == ("POST", "/seal"):
            self.sealed = True
            self.save()
            return self.status()
        if (method, path) == ("GET", "/prompt"):
            return {"system_prompt": self.prompt}
        if (method, path) == ("GET", "/observe"):
            return self.call("observe") if self.steps else self.initial
        if (method, path) == ("POST", "/step"):
            return self.execute(payload.get("number"), payload.get("code"))
        raise ValueError("Unknown operation")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def handle_request(self):
        episode = self.server.episode
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 <= length <= 1024 * 1024:
                raise ValueError("Request exceeds the 1 MiB transport limit")
            payload = json.loads(self.rfile.read(length)) if length else {}
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object")
            result = episode.dispatch(self.command, self.path, payload)
            status = 200
        except ValueError as error:
            status, result = 400, {"error": str(error)}
        except Exception as error:
            # The engine could already have applied an action. Never retry that step.
            if episode.fault is None:
                episode.fault = f"Native environment failure ({type(error).__name__}): {error}"
                episode.save()
            status, result = 503, {"error": episode.fault}
        body = json.dumps(result).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = handle_request
    timeout = 15


if __name__ == "__main__":
    from socketserver import UnixStreamServer

    sock = Path("/channel/game.sock")
    with UnixStreamServer(str(sock), Handler) as server:
        server.episode = Episode(native, Path("/evidence/episode.json"))
        os.chmod(sock, 0o666)
        server.serve_forever()
