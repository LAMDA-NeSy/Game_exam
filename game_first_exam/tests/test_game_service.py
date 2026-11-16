"""Protocol trust-boundary and accounting checks against the shared live service."""
import copy
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "game_first_exam/runtime"))
sys.path.insert(0, str(ROOT / "scripts"))
from game_schemas import register_schemas

register_schemas()
from contracts import Capabilities, Transition
from grade import grade
from server import Game, Handler, HTTPServer


class Backend:
    def __init__(self):
        self.position = 0
        self.closed = False

    def spec(self):
        return {"adapter_version": "1.0.0", "capabilities": Capabilities(False, "enum", native_truncation=True).to_dict(), "action_schema": {"type": "string", "enum": ["forward", "noop", "crash"]}}

    def observe(self):
        return {"position": self.position}

    def step(self, action):
        if action == "crash":
            raise RuntimeError("native command failure")
        if action == "forward":
            self.position += 1
        return Transition(float(action == "forward"), self.position == 2)

    def metrics(self):
        return {"score": self.position, "success": int(self.success())}

    def success(self):
        return self.position == 2

    def fingerprint(self):
        return str(self.position) * 64

    def frame(self):
        return np.zeros((16, 16, 3), dtype=np.uint8)

    def close(self):
        self.closed = True


def instance():
    config = json.loads((ROOT / "game_first_exam/tasks/minigrid/minigrid-doorkey-i01-standard/tests/instance.json").read_text())
    config.update(seed=3, max_steps=4, initial_state_sha256="0" * 64)
    return config


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.backend = Backend()
        self.game = Game(self.backend, instance(), self.directory.name)

    def tearDown(self):
        self.game.close()
        self.directory.cleanup()

    def send(self, action, rid=None):
        return self.game.submit({"action": action, "expected_step": self.game.steps,
                                 "request_id": rid or str(self.game.steps)})

    def test_no_public_action_cap_keeps_native_end_and_wall_clock(self):
        config = instance(); config['max_steps'] = None
        with tempfile.TemporaryDirectory() as out:
            game = Game(Backend(), config, out, wall_clock=600)
            try:
                for i in range(5):
                    game.submit({'action': 'noop', 'expected_step': i, 'request_id': str(i)})
                self.assertIsNone(game.final)
                self.assertIsNone(game.observe()['steps_remaining'])
                game.submit({'action': 'forward', 'expected_step': 5, 'request_id': 'f1'})
                game.submit({'action': 'forward', 'expected_step': 6, 'request_id': 'f2'})
                self.assertEqual(game.final['reason'], 'native_terminated')
                self.assertFalse(game.final['budget_exhausted'])
                self.assertEqual(grade(game.final, config, lambda f, i: None)['success'], 1)
                bad = copy.deepcopy(game.final); bad['budget_exhausted'] = True
                with self.assertRaises(ValueError): grade(bad, config, lambda f, i: None)
            finally: game.close()
        with tempfile.TemporaryDirectory() as out:
            game = Game(Backend(), config, out, wall_clock=600)
            try:
                game.observe(); game.started -= 601; game.observe()
                self.assertEqual(game.final['reason'], 'time_limit')
                self.assertFalse(game.final['budget_exhausted'])
                self.assertEqual(grade(game.final, config, lambda f, i: None)['success'], 0)
            finally: game.close()

    def test_exactly_once_retry_and_stale_rejection(self):
        body = {"action": "forward", "expected_step": 0, "request_id": "request-1"}
        first = self.game.submit(body)
        self.assertEqual(self.game.submit(body), first)
        self.assertEqual(self.backend.position, 1)
        for change in ({"action": "noop"}, {"request_id": "different"}):
            with self.assertRaises(ValueError):
                self.game.submit({**body, **change})
        self.assertEqual(self.game.steps, 1)

    def test_invalid_actions_and_reads_do_not_advance(self):
        for _ in range(3):
            self.game.observe()
            self.game.spec()
        for action in ("reset", "unknown", 1, {"action": "forward"}):
            with self.assertRaises(ValueError):
                self.send(action)
        self.assertEqual((self.game.steps, self.backend.position), (0, 0))

    def test_final_is_immutable_and_grade_binds_instance(self):
        self.send("forward")
        self.send("forward")
        evidence = Path(self.directory.name, "final.json").read_bytes()
        self.game.finalize("agent_finished")
        with self.assertRaises(ValueError):
            self.send("noop")
        self.assertEqual(Path(self.directory.name, "final.json").read_bytes(), evidence)
        self.assertEqual(grade(self.game.final, instance(), lambda f, i: None)["success"], 1)
        other = instance(); other["seed"] += 1
        with self.assertRaises(ValueError):
            grade(self.game.final, other, lambda f, i: None)
        altered = copy.deepcopy(self.game.final); altered["steps"] = 99
        with self.assertRaises(ValueError):
            grade(altered, instance(), lambda f, i: None)

    def test_budget_failure_is_valid_but_environment_fault_is_not(self):
        for _ in range(4):
            self.send("noop")
        self.assertEqual(self.game.final["reason"], "step_limit")
        self.assertEqual(grade(self.game.final, instance(), lambda f, i: None)["success"], 0)
        with tempfile.TemporaryDirectory() as out:
            game = Game(Backend(), instance(), out)
            with self.assertRaises(RuntimeError):
                game.submit({"action": "crash", "expected_step": 0, "request_id": "crash"})
            result = grade(game.final, instance(), lambda f, i: None)
            self.assertEqual((result["success"], result["sim_error"], result["infra_error"]), (0, 1, 1))
            game.close()

    def test_wall_clock_starts_on_observation_not_construction(self):
        self.assertIsNone(self.game.started)
        self.game.spec()
        self.assertIsNone(self.game.started)
        self.game.observe()
        self.game.started -= 601
        self.game.check_time()
        self.assertEqual(self.game.final["reason"], "time_limit")
        with self.assertRaises(ValueError):
            self.send("forward")

    def test_http_surface_does_not_expose_hidden_controls(self):
        server = HTTPServer(("127.0.0.1", 0), Handler)
        server.game = self.game
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            for path in ("/state", "/reset", "/success", "/final.json", "/../instance.json"):
                for data in (None, b"{}"):
                    with self.assertRaises(urllib.error.HTTPError) as exc:
                        opener.open(urllib.request.Request(base + path, data=data))
                    self.assertEqual(exc.exception.code, 404)
            self.assertEqual(self.game.steps, 0)
        finally:
            server.shutdown(); server.server_close(); thread.join()



if __name__ == "__main__":
    unittest.main()
