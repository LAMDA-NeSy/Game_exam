"""Trusted synchronous game session. Engine faults are invalid results, never model failures."""
import argparse
import copy
import hashlib
import json
import math
import os
import re
import signal
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from config_schema import PROTOCOL, positive, validate_instance, validate_spec
from contracts import Transition
from recording import Recorder


class EnvironmentFault(RuntimeError):
    pass


class InvalidAction(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class Game:
    def _setup(self, instance, output, wall_clock):
        validate_instance(instance)
        positive(wall_clock, "wall_clock")
        self.instance = copy.deepcopy(instance)
        self.output = Path(output)
        self.wall_clock = float(wall_clock)
        self.max_steps = instance["max_steps"]
        self.steps, self.reward = 0, 0.0
        self.invalid_actions = 0
        self.terminated = self.truncated = False
        self.started = self.final = None
        self.adapter = self.initial_hash = None
        self.requests, self._spec = {}, {}
        self._observation = None
        self.recorder = Recorder(output)
        self.recorder.event({"event": "start", "instance_sha256": digest(instance)})

    @classmethod
    def open(cls, factory, instance, assets, output, wall_clock=600):
        # Bad configuration is rejected before constructing an engine. A broken engine still leaves evidence.
        validate_instance(instance)
        positive(wall_clock, "wall_clock")
        try:
            adapter = factory(instance, assets)
        except Exception as exc:  # noqa: BLE001 - explicit environment fault boundary
            game = cls.__new__(cls)
            game._setup(instance, output, wall_clock)
            game.fault(exc, "construction")
            return game
        return cls(adapter, instance, output, wall_clock)

    def __init__(self, adapter, instance, output, wall_clock=600):
        self._setup(instance, output, wall_clock)
        self.adapter = adapter
        try:
            self._spec = copy.deepcopy(validate_spec(adapter.spec(), instance))
            self.initial_hash = adapter.fingerprint()
            if self.initial_hash != instance["initial_state_sha256"]:
                raise ValueError("frozen initial state mismatch")
            self.record_frame()
            self.capture_observation()
        except Exception as exc:  # noqa: BLE001 - explicit environment fault boundary
            self.fault(exc, "initialization")

    def start(self):
        if self.started is None and self.final is None:
            self.started = time.monotonic()

    def check_time(self):
        if self.started is not None and time.monotonic() - self.started >= self.wall_clock:
            self.finalize("time_limit")

    def spec(self):
        return {**copy.deepcopy(self._spec), "protocol": PROTOCOL, "reset_budget": 0,
                "max_steps": self.max_steps, "timing": "action-stepped",
                "observation_profile": self.instance["observation_profile"]}

    def observe(self):
        self.start()
        self.check_time()
        elapsed = 0 if self.started is None else time.monotonic() - self.started
        return {"step": self.steps, "done": self.final is not None,
                "steps_remaining": None if self.max_steps is None else self.max_steps - self.steps,
                "time_left_s": max(0, self.wall_clock - elapsed), "observation": copy.deepcopy(self._observation)}

    def capture_observation(self):
        observation = self.adapter.observe()
        if not isinstance(observation, dict):
            raise TypeError("observation must be an object")
        json.dumps(observation, allow_nan=False)
        self._observation = copy.deepcopy(observation)

    def record_frame(self):
        frame = self.adapter.frame()
        if frame is not None and (getattr(frame, "ndim", None) != 3 or frame.shape[-1] != 3 or str(frame.dtype) != "uint8"):
            raise TypeError("frame must be an HxWx3 uint8 RGB array or None")
        self.recorder.frame(frame)

    def reject_action(self, message):
        self.invalid_actions += 1
        self.recorder.event({"event": "request_rejected", "category": "invalid_action", "step": self.steps})
        raise InvalidAction(message)

    def submit(self, body):
        self.check_time()
        if not isinstance(body, dict) or set(body) != {"action", "expected_step", "request_id"}:
            raise ValueError("require action, expected_step, request_id only")
        action, step, rid = body["action"], body["expected_step"], body["request_id"]
        if type(step) is not int or not isinstance(rid, str) or not 1 <= len(rid) <= 80:
            raise ValueError("invalid step or request_id")
        if rid in self.requests:
            old_body, response = self.requests[rid]
            if old_body != body:
                raise ValueError("request_id reused with different payload")
            return copy.deepcopy(response)
        if self.final is not None:
            raise ValueError("episode closed")
        if step != self.steps:
            raise ValueError("stale expected_step; observe before acting")
        schema = self._spec["action_schema"]
        if not isinstance(action, str) or not action or len(action) > schema.get("max_length", 256):
            self.reject_action("invalid action string")
        if "enum" in schema and action not in schema["enum"]:
            self.reject_action("unknown action")
        if "pattern" in schema and re.fullmatch(schema["pattern"], action) is None:
            self.reject_action("action outside the declared command grammar")
        self.start()
        self.steps += 1
        try:
            transition = self.adapter.step(action)
            if not isinstance(transition, Transition) or type(transition.reward) not in (int, float) or not math.isfinite(transition.reward):
                raise TypeError("step must return Transition with a finite reward increment")
            if type(transition.terminated) is not bool or type(transition.truncated) is not bool:
                raise TypeError("native flags must be boolean")
            if transition.truncated and not self.instance["capabilities"]["native_truncation"]:
                raise ValueError("adapter returned undeclared native truncation")
            self.reward += float(transition.reward)
            self.terminated, self.truncated = transition.terminated, transition.truncated
            self.recorder.event({"event": "step", "step": self.steps, "action": action,
                                 "request_id": rid, "reward": transition.reward,
                                 "state_sha256": self.adapter.fingerprint()})
            self.record_frame()
            self.capture_observation()
            if self.terminated:
                self.finalize("native_terminated")
            elif self.truncated:
                self.finalize("native_truncated")
            elif self.max_steps is not None and self.steps >= self.max_steps:
                self.finalize("step_limit")
        except Exception as exc:
            self.fault(exc, "step")
            raise EnvironmentFault("environment execution failed; attempt is invalid") from exc
        response = self.observe()
        self.requests[rid] = (copy.deepcopy(body), copy.deepcopy(response))
        return response

    def fault(self, exc, phase):
        if self.final is not None:
            return
        self.recorder.event({"event": "environment_error", "step": self.steps,
                             "phase": phase, "exception": type(exc).__name__, "message": str(exc)})
        self._seal("environment_error", None, None, {"phase": phase, "exception": type(exc).__name__})

    def finalize(self, reason):
        if self.final is not None:
            return
        try:
            success, metrics = self.adapter.success(), self.adapter.metrics()
            if type(success) is not bool or not isinstance(metrics, dict):
                raise TypeError("success/metrics violate the adapter contract")
            json.dumps(metrics, allow_nan=False)
        except Exception as exc:  # noqa: BLE001 - no guessed score after a broken metric callback
            self.fault(exc, "metrics")
            return
        self._seal(reason, success, metrics)

    def _seal(self, reason, success, metrics, error=None):
        source = {"native_terminated": "native", "native_truncated": "native", "step_limit": "budget",
                  "time_limit": "budget", "agent_finished": "agent", "environment_error": "environment"}[reason]
        final = {"schema": PROTOCOL, "finalized": True, "benchmark": self.instance["benchmark"],
                 "env_id": self.instance["env_id"], "seed": self.instance["seed"],
                 "instance_sha256": digest(self.instance), "initial_state_sha256": self.initial_hash,
                 "success": success, "terminated": self.terminated, "truncated": self.truncated,
                 "steps": self.steps, "max_steps": self.max_steps, "return": self.reward,
                 "invalid_actions": self.invalid_actions,
                 "reason": reason, "end_source": source, "budget_exhausted": self.max_steps is not None and self.steps >= self.max_steps,
                 "result_valid": error is None, "error_category": "environment" if error else None,
                 "error": error, "sim_error": int(error is not None),
                 "elapsed_seconds": 0.0 if self.started is None else time.monotonic() - self.started,
                 "metrics": metrics, "video_source": "live"}
        temporary = self.output / "final.json.tmp"
        temporary.write_text(json.dumps(final, indent=2, allow_nan=False) + "\n")
        temporary.replace(self.output / "final.json")
        self.final = final
        self.recorder.event({"event": "final", **final})
        self.recorder.close()

    def close(self):
        self.finalize("agent_finished")
        if self.adapter is not None:
            self.adapter.close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, code, data):
        encoded = json.dumps(data, allow_nan=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        game = self.server.game
        game.check_time()
        try:
            if self.path == "/spec":
                return self.reply(200, game.spec())
            if self.path == "/observe":
                return self.reply(200, game.observe())
            if self.path == "/status":
                return self.reply(200, {"step": game.steps, "done": game.final is not None})
            self.reply(404, {"error": "unknown endpoint"})
        except EnvironmentFault:
            self.reply(500, {"error_category": "environment", "error": "environment unavailable"})

    def do_POST(self):
        if self.path != "/submit":
            return self.reply(404, {"error": "unknown endpoint"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4096:
                raise ValueError("body must be 1..4096 bytes")
            body = json.loads(self.rfile.read(length))
            self.reply(200, self.server.game.submit(body))
        except InvalidAction as exc:
            self.reply(400, {"error_category": "invalid_action", "error": str(exc)})
        except (ValueError, TypeError) as exc:
            self.reply(400, {"error_category": "invalid_request", "error": str(exc)})
        except EnvironmentFault:
            self.reply(500, {"error_category": "environment", "error": "environment unavailable"})

    def setup(self):
        super().setup()
        self.connection.settimeout(3)


def main():
    from adapter import Adapter
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", default="/srv/instance.json")
    parser.add_argument("--output", default="/data")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    instance = json.loads(Path(args.instance).read_text())
    game = Game.open(Adapter, instance, Path(args.instance).parent, args.output,
                     float(os.environ.get("RCB_WALL_CLOCK_S", "600")))
    server = HTTPServer((args.host, args.port), Handler)
    server.game, server.timeout = game, 0.25
    finish = collect = False

    def stop(signum, _frame):
        nonlocal finish, collect
        if signum == signal.SIGUSR1:
            collect = True
        else:
            finish = True

    signal.signal(signal.SIGUSR1, stop)
    signal.signal(signal.SIGTERM, stop)
    (game.output / "server.pid").write_text(str(os.getpid()))
    try:
        while not finish:
            if collect:
                game.finalize("agent_finished")
                (game.output / "collection.ready").touch()
                collect = False
            server.handle_request()
            game.check_time()
    finally:
        game.close()
        server.server_close()


if __name__ == "__main__":
    main()
