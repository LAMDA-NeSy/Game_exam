"""GameWorld 25_01, played against the native single-player opponent."""
from base64 import b64decode
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlsplit

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

from contracts import Capabilities, Transition
from encoding import png, state_hash

MOVES = {"wait": (), "left": ("a",), "right": ("d",), "brake": ("s",),
         "jump": ("w",), "jump_left": ("a", "w"), "jump_right": ("d", "w"),
         "boost_left": ("a", "Space"), "boost_right": ("d", "Space"),
         "jump_boost_right": ("d", "w", "Space"), "jump_boost_left": ("a", "w", "Space")}
ORIGIN = "http://pitch.test"


class Adapter:
    def __init__(self, instance, assets=None):
        self.stack = ExitStack()
        try:
            self.load(Path(assets) / "game")
        except BaseException:
            self.close()
            raise

    def load(self, root):
        root = root.resolve(strict=True)
        driver = self.stack.enter_context(sync_playwright())
        browser = driver.chromium.launch(args=["--mute-audio"])
        self.stack.callback(browser.close)
        self.page = browser.new_page(viewport={"width": 1024, "height": 384})

        self.cdp = self.page.context.new_cdp_session(self.page)

        def serve(route):
            url = urlsplit(route.request.url)
            path = (root / unquote(url.path).lstrip("/")).resolve()
            if url.netloc == "pitch.test" and path.is_relative_to(root) and path.is_file():
                route.fulfill(path=path)
            else:
                route.abort()

        self.page.route("**/*", serve)
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.page.clock.install(time=start)
        self.page.clock.pause_at(start + timedelta(seconds=1))
        self.page.goto(ORIGIN + "/index.html?player=1", wait_until="domcontentloaded")
        # Stop on the first playable animation frame, including on a cold browser cache.
        for _ in range(2500):
            self.page.clock.run_for(16)
            state = self.page.evaluate("() => window.gameAPI?.getState()")
            if state and state["is_actionable"]:
                if state["game_state"]["environment"]["room_name"] == "rm_game":
                    self.state = state
                    break
        else:
            raise RuntimeError("Single-player match did not start")
        if self.score() != (0, 0) or self.state["seed"] != 42:
            raise RuntimeError("Unexpected kickoff")
        self.steps = 0
        self.capture()

    def spec(self):
        return {"adapter_version": "1.0.0", "capabilities": Capabilities(True, "enum").to_dict(),
                "action_schema": {"type": "string", "enum": list(MOVES)},
                "actions": "Hold one movement for 160 milliseconds of match time.",
                "goal": "Score the first goal against the native AI."}

    def capture(self):
        # DevTools captures the composited frame without advancing the paused game clock.
        shot = self.cdp.send("Page.captureScreenshot", {"format": "png", "fromSurface": True})
        data = b64decode(shot["data"])
        with Image.open(BytesIO(data)) as image:
            self.rgb = np.array(image.convert("RGB"))

    def frame(self):
        return self.rgb

    def observe(self):
        return {"image_png_base64": png(self.rgb)}

    def step(self, action):
        if action not in MOVES or self.score() != (0, 0):
            raise ValueError("Invalid input or finished match")
        keys = MOVES[action]
        for key in keys:
            self.page.keyboard.down(key)
        try:
            self.page.clock.run_for(160)
        finally:
            for key in reversed(keys):
                self.page.keyboard.up(key)
        self.steps += 1
        self.state = self.page.evaluate("gameAPI.getState()")
        self.capture()
        return Transition(float(self.success()), self.score() != (0, 0))

    def score(self):
        metrics = self.state["metrics"]
        score = metrics["goals_for"], metrics["goals_against"]
        if any(type(value) is not int for value in score):
            raise RuntimeError("Native scoreboard unavailable")
        return score

    def success(self):
        return self.score() == (1, 0)

    def metrics(self):
        own, opponent = self.score()
        return {"goals_for": own, "goals_against": opponent, "success": int(self.success())}

    def fingerprint(self):
        board = self.state["game_state"]
        return state_hash({"seed": self.state["seed"], "room": board["environment"]["room_name"],
                           "player": board["player"], "entities": board["entities"],
                           "score": self.score(), "steps": self.steps})

    def close(self):
        self.stack.close()
