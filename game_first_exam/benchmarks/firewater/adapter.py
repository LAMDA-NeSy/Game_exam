"""Forest Temple level one, scored by its native terminal outcome."""
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

MOVES = {
    "wait": (), "left": ("left",), "right": ("right",),
    "jump_left": ("jump", "left"), "jump_right": ("jump", "right"),
}
KEYS = {
    "fireboy": {"left": "ArrowLeft", "right": "ArrowRight", "jump": "ArrowUp"},
    "watergirl": {"left": "a", "right": "d", "jump": "w"},
}
ORIGIN = "http://forest.test"


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
        self.page = browser.new_page(viewport={"width": 800, "height": 600})

        self.cdp = self.page.context.new_cdp_session(self.page)

        def serve(route):
            url = urlsplit(route.request.url)
            path = (root / unquote(url.path).lstrip("/")).resolve()
            if url.netloc == "forest.test" and path.is_relative_to(root) and path.is_file():
                route.fulfill(path=path)
            else:
                route.abort()

        self.page.route("**/*", serve)
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.page.clock.install(time=start)
        self.page.clock.pause_at(start + timedelta(seconds=1))
        self.page.goto(ORIGIN + "/index.html?level=1", wait_until="domcontentloaded")
        for _ in range(160):
            self.page.clock.run_for(250)
            state = self.page.evaluate("() => window.gameAPI?.getState()")
            if state and state["is_actionable"]:
                board = state["game_state"]
                if all(board["diamonds"][r]["total"] for r in KEYS) and board["level"] == 1:
                    self.state = state
                    break
        else:
            raise RuntimeError("GameWorld did not initialize forest level 1")
        # Let the native opening animation settle before accepting the first action.
        self.page.clock.run_for(4000)
        self.state = self.page.evaluate("gameAPI.getState()")
        # Count native updates. Phaser can render a frame without advancing the physics.
        self.page.evaluate("""() => {
            const game = window.__fbwg_game || window.Phaser.GAMES[0];
            window.forestTicks = 0;
            game.plugins.add({postUpdate() { window.forestTicks++; }});
        }""")
        self.steps = 0
        self.capture()

    def spec(self):
        return {"adapter_version": "1.0.0", "capabilities": Capabilities(True, "enum").to_dict(),
                "action_schema": {"type": "string", "enum": [f"{a}/{b}" for a in MOVES for b in MOVES]},
                "actions": "fireboy/watergirl, six native updates per paired move",
                "goal": "Guide both characters into their matching exits on forest level one."}

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
        moves = action.split("/")
        if len(moves) != 2 or any(move not in MOVES for move in moves):
            raise ValueError("expected two role moves")
        if self.state["terminal"]["isTerminal"]:
            raise ValueError("episode already ended")
        keys = [KEYS[role][direction] for role, move in zip(KEYS, moves) for direction in MOVES[move]]
        for key in keys:
            self.page.keyboard.down(key)
        try:
            target = self.page.evaluate("window.forestTicks") + 6
            self.page.clock.run_for(96)
            for _ in range(16):
                ticks = self.page.evaluate("window.forestTicks")
                if ticks == target:
                    break
                if ticks > target:
                    raise RuntimeError("native updates exceeded action interval")
                if self.page.evaluate("gameAPI.getState().terminal.isTerminal"):
                    break
                self.page.clock.run_for(16)
            else:
                raise RuntimeError("native game stopped advancing")
        finally:
            for key in reversed(keys):
                self.page.keyboard.up(key)
        self.steps += 1
        self.state = self.page.evaluate("gameAPI.getState()")
        self.capture()
        won = self.success()
        return Transition(float(won), self.state["terminal"]["isTerminal"])

    def counts(self):
        gems = self.state["game_state"]["diamonds"]
        return {role: gems[role]["collected"] for role in KEYS}

    def success(self):
        terminal = self.state["terminal"]
        return (self.state["game_state"]["level"] == 1 and terminal["isTerminal"]
                and terminal["outcome"] == "success" and terminal["reason"] == "level_completed")

    def metrics(self):
        return {**self.counts(), "success": int(self.success()), "level": self.state["game_state"]["level"],
                "terminal_outcome": self.state["terminal"]["outcome"],
                "terminal_reason": self.state["terminal"]["reason"]}

    def fingerprint(self):
        board = self.state["game_state"]
        positions = []
        for role in ("player", "watergirl"):
            body = board.get(role) or {}
            positions.append([round(body[axis] / 8) if body.get(axis) is not None else None
                              for axis in ("x", "y")])
        return state_hash({"level": board["level"], "positions": positions, "gems": self.counts(),
                           "steps": self.steps, "game_over": self.state["terminal"]["isTerminal"]})

    def close(self):
        self.stack.close()
