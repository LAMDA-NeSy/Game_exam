"""Play the pinned GameWorld Pac-Man snapshot with paused browser time."""

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

KEYS = {"wait": None, "up": "ArrowUp", "down": "ArrowDown", "left": "ArrowLeft", "right": "ArrowRight"}
ORIGIN = "http://pacman.test"
TARGET_SCORE = 600


class Adapter:
    def __init__(self, instance, assets=None):
        self.resources = ExitStack()
        try:
            self.start((Path(assets) / "game").resolve())
        except BaseException:
            self.close()
            raise

    def start(self, root):
        driver = self.resources.enter_context(sync_playwright())
        browser = driver.chromium.launch(args=["--mute-audio"])
        self.resources.callback(browser.close)
        self.page = browser.new_page(viewport={"width": 854, "height": 480})

        def serve(route):
            url = urlsplit(route.request.url)
            path = (root / unquote(url.path).lstrip("/")).resolve()
            if url.netloc == "pacman.test" and path.is_relative_to(root) and path.is_file():
                route.fulfill(path=path)
            else:
                route.abort()

        self.page.route("**/*", serve)
        self.cdp = self.page.context.new_cdp_session(self.page)
        opening = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.page.clock.install(time=opening)
        self.page.clock.pause_at(opening + timedelta(seconds=1))
        self.page.goto(ORIGIN + "/index.html", wait_until="domcontentloaded")
        for _ in range(1000):
            self.page.clock.run_for(50)
            self.state = self.page.evaluate("() => window.gameAPI?.getState()")
            if self.state and self.state["status"] == "playing":
                break
        else:
            raise RuntimeError(f"Pac-Man did not start: {self.state}")
        if self.state["game_state"]["score"] is None:
            raise RuntimeError("Native score unavailable at start")
        self.capture()

    def spec(self):
        return {"adapter_version": "1.0.0", "capabilities": Capabilities(True, "enum").to_dict(),
                "action_schema": {"type": "string", "enum": list(KEYS)},
                "goal": "Earn at least 600 points before native game over."}

    def success(self):
        return self.state["game_state"]["score"] >= TARGET_SCORE

    def done(self):
        return self.success() or self.state["terminal"]["isTerminal"]

    def step(self, action):
        if self.done() or action not in KEYS:
            raise ValueError("Expected a legal action during a live game")
        key = KEYS[action]
        if key:
            self.page.keyboard.down(key)
        try:
            # Keep native timers and collisions moving for half a second.
            for _ in range(10):
                self.page.clock.run_for(50)
                self.state = self.page.evaluate("gameAPI.getState()")
                if self.done():
                    break
        finally:
            if key:
                self.page.keyboard.up(key)
        self.capture()
        return Transition(float(self.success()), self.done())

    def metrics(self):
        return {"score": self.state["game_state"]["score"],
                "deaths": self.state["metrics"]["deaths"], "success": int(self.success())}

    def fingerprint(self):
        return state_hash({"score": self.state["game_state"]["score"]})

    def capture(self):
        data = self.cdp.send("Page.captureScreenshot", {"format": "png"})["data"]
        with Image.open(BytesIO(b64decode(data))) as image:
            self.rgb = np.array(image.convert("RGB"))

    def observe(self):
        return {"image_png_base64": png(self.rgb)}

    def frame(self):
        return self.rgb

    def close(self):
        self.resources.close()
