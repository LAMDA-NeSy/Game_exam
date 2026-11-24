"""Play the first numbered Vex 3 act using keyboard input and native outcomes."""
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

KEYS = {
    "wait": (),
    "right": ("ArrowRight",),
    "left": ("ArrowLeft",),
    "jump": ("ArrowUp",),
    "jump_right": ("ArrowRight", "ArrowUp"),
    "jump_left": ("ArrowLeft", "ArrowUp"),
    "slide": ("ArrowRight", "ArrowDown"),
}
ORIGIN = "http://vex.test"


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
        self.page = browser.new_page(viewport={"width": 800, "height": 600})

        def serve(route):
            url = urlsplit(route.request.url)
            path = (root / unquote(url.path).lstrip("/")).resolve()
            if url.netloc == "vex.test" and path.is_relative_to(root) and path.is_file():
                route.fulfill(path=path)
            else:
                route.abort()

        self.page.route("**/*", serve)
        self.cdp = self.page.context.new_cdp_session(self.page)
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.page.clock.install(time=start)
        self.page.clock.pause_at(start + timedelta(seconds=1))
        self.page.goto(ORIGIN + "/index.html?level=1", wait_until="domcontentloaded")
        for _ in range(1000):
            self.page.clock.run_for(64)
            self.state = self.page.evaluate("() => window.gameAPI?.getState()")
            if self.state and self.state["is_actionable"] and str(self.state["game_state"]["level"]) == "1":
                break
        else:
            raise RuntimeError(f"Act 1 did not open: {self.state}")
        if self.state["metrics"]["deaths"] != 0:
            raise RuntimeError("Act 1 opened after a death")
        # The player spawns above the floor. Anchor the opening to first contact.
        for _ in range(120):
            player = self.state["game_state"]["player"]
            if player and player["state"] == "0" and player["vx"] == player["vy"] == 0:
                break
            self.page.clock.run_for(16)
            self.state = self.page.evaluate("gameAPI.getState()")
            if self.done():
                raise RuntimeError("Act ended before the player reached the floor")
        else:
            raise RuntimeError(f"Act 1 did not settle at spawn: {player}")
        # The same grounded player can leave the 30 Hz Phaser accumulator
        # at different offsets after loading. Start each episode at one
        # fixed offset so a 64 ms action produces the same native ticks.
        self.page.evaluate("() => { window.__vex3Game._deltaTime = 44 / 3; }")
        self.capture()

    def spec(self):
        return {
            "adapter_version": "1.0.0",
            "capabilities": Capabilities(True, "enum").to_dict(),
            "action_schema": {"type": "string", "enum": list(KEYS)},
            "goal": "Finish Act 1 without dying.",
        }

    def success(self):
        return (str(self.state["game_state"]["level"]) == "1" and
                self.state["metrics"]["deaths"] == 0 and self.state["terminal"]["outcome"] == "success")

    def done(self):
        return self.state["terminal"]["isTerminal"] or self.state["metrics"]["deaths"] > 0

    def step(self, action):
        if self.done() or action not in KEYS:
            raise ValueError("Expected a legal action in a live act")
        for key in KEYS[action]:
            self.page.keyboard.down(key)
        try:
            for _ in range(4):
                self.page.clock.run_for(16)
                self.state = self.page.evaluate("gameAPI.getState()")
                if self.done():
                    break
        finally:
            for key in KEYS[action]:
                self.page.keyboard.up(key)
        self.capture()
        return Transition(float(self.success()), self.done())

    def metrics(self):
        metrics = self.state["metrics"]
        return {
            "deaths": metrics["deaths"],
            "checkpoints_passed": metrics["checkpoints_passed"],
            "success": int(self.success()),
        }

    def fingerprint(self):
        board = self.state["game_state"]
        return state_hash({
            "level": board["level"],
            "player": board["player"],
            "deaths": self.state["metrics"]["deaths"],
            "success": int(self.success()),
        })

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
