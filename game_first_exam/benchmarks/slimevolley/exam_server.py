"""Trusted service for the SlimeVolley practice and scored phases."""
import json
import os
import signal
import sys
import tempfile
from http.server import HTTPServer
from pathlib import Path
from uuid import uuid4

from adapter import Adapter
from server import EnvironmentFault, Game, Handler

DATA = Path("/data")
ASSETS = Path("/srv")


class PracticeGame(Game):
    def record_frame(self):
        # The public pixel stream remains available. Only the scored match is recorded.
        pass


class PracticeServer(HTTPServer):
    def __init__(self, instances, scratch):
        super().__init__(("0.0.0.0", 8000), PracticeHandler)
        self.instances, self.scratch = instances, scratch
        self.summary = {slot: {"episodes": 0, "steps": 0, "errors": 0} for slot in instances}
        self.game = None
        self.start("A")

    def finish_episode(self):
        if self.game is not None:
            self.game.close()
            totals = self.summary[self.slot]
            totals["steps"] += self.game.steps
            totals["errors"] += int(not self.game.final["result_valid"])
            self.episode_dir.cleanup()
            self.game = None

    def start(self, slot):
        self.finish_episode()
        self.slot = slot
        self.episode_dir = tempfile.TemporaryDirectory(dir=self.scratch)
        self.game = PracticeGame.open(Adapter, self.instances[slot], ASSETS, self.episode_dir.name)
        self.summary[slot]["episodes"] += 1
        return {"slot": slot, **self.game.observe()}


class PracticeHandler(Handler):
    def do_POST(self):
        if self.path != "/practice/start":
            return super().do_POST()
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 64:
                raise ValueError
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict) or set(body) != {"slot"} or body["slot"] not in ("A", "B"):
                raise ValueError
        except ValueError:
            return self.reply(400, {"error": "provide exactly one slot: A or B"})
        self.reply(200, self.server.start(body["slot"]))


def serve(make_server, seal):
    # Keep all simulator work out of the signal handlers.
    collecting = False
    stopping = False

    def stop(signum, _frame):
        nonlocal collecting, stopping
        if signum == signal.SIGUSR1:
            collecting = True
        else:
            stopping = True

    DATA.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGUSR1, stop)
    signal.signal(signal.SIGTERM, stop)
    with make_server() as server:
        server.timeout = 0.25
        (DATA / "server.pid").write_text(str(os.getpid()))
        while not collecting and not stopping:
            server.handle_request()
        # After collection starts, stop accepting public requests before computing evidence.
        if collecting:
            seal(server)
            (DATA / "collection.ready").touch()
            # Harbor still needs to copy the artifacts from this container.
            while not stopping:
                signal.pause()


def practice():
    instances = json.loads((ASSETS / "practice-instances.json").read_text())

    def seal(server):
        server.finish_episode()
        (DATA / "practice.json").write_text(json.dumps(server.summary) + "\n")

    with tempfile.TemporaryDirectory() as scratch:
        serve(lambda: PracticeServer(instances, scratch), seal)


def official():
    instance = json.loads((ASSETS / "instance.json").read_text())

    def make_server():
        server = HTTPServer(("0.0.0.0", 8000), Handler)
        # The host enforces the policy deadline. Keep time available for trusted idle steps.
        server.game = Game.open(Adapter, instance, ASSETS, DATA, wall_clock=3600)
        return server

    def seal(server):
        game = server.game
        controller_steps = game.steps
        try:
            while game.final is None:
                game.submit({"action": "idle", "expected_step": game.steps, "request_id": uuid4().hex})
        except EnvironmentFault:
            pass  # The existing grader rejects the engine's invalid verdict.
        finally:
            game.close()
        result = {"controller_steps": controller_steps, "idle_steps": game.steps - controller_steps}
        (DATA / "rollout.json").write_text(json.dumps(result) + "\n")

    serve(make_server, seal)


def instances():
    base = json.loads((ASSETS / "instance.json").read_text())
    result = {}
    for slot, seed in json.load(sys.stdin).items():
        instance = {**base, "seed": seed}
        adapter = Adapter(instance, ASSETS)
        try:
            result[slot] = {**instance, "initial_state_sha256": adapter.fingerprint()}
        finally:
            adapter.close()
    print(json.dumps(result))


if __name__ == "__main__":
    {"practice": practice, "official": official, "instances": instances}[sys.argv[1]]()
