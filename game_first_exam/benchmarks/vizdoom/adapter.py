"""Use the native single-player engine and expose player-facing observations."""
import hashlib
import importlib.metadata
from pathlib import Path
import re
import tempfile

import vizdoom as vzd

from contracts import Transition
from encoding import png, state_hash
from instance_schema import SCENARIOS
from vizdoom_actions import DELTA_BUTTONS, DURATION, dense_pattern


class Adapter:
    def __init__(self, instance, assets):
        self.instance = instance
        self.default_tics = instance["tics_per_decision"]
        self.variable_tics = self.default_tics == 1
        self.action_tics = []
        for package, expected in instance["engine_versions"].items():
            if importlib.metadata.version(package) != expected:
                raise ValueError(f"ViZDoom dependency version mismatch: {package}")
        installed = Path(vzd.__file__).resolve().parent
        for relative, expected in instance["scenario_hashes"].items():
            if hashlib.sha256((installed / relative).read_bytes()).hexdigest() != expected:
                raise ValueError(f"ViZDoom asset mismatch: {relative}")

        family = instance["family"]
        scene = SCENARIOS[family]
        scenario = scene["stem"]
        self.buttons = instance["buttons"]
        self.delta_buttons = [button for button in self.buttons if button in DELTA_BUTTONS]
        self.binary_buttons = [button for button in self.buttons if button not in DELTA_BUTTONS]
        self.actions = []
        if not self.delta_buttons:
            for mask in range(1 << len(self.buttons)):
                action = "+".join(button for i, button in enumerate(self.buttons) if mask & (1 << i))
                self.actions.append(action or "noop")

        self.goal = scene["goal"]
        self.goal_variable = {"kill": vzd.GameVariable.KILLCOUNT, "vest": vzd.GameVariable.ARMOR,
                              "green-vest": vzd.GameVariable.ARMOR}.get(self.goal)
        self.goal_value = 100 if self.goal in ("vest", "green-vest") else 1
        self.stats = scene.get("stats", ())
        self.expose_notifications = instance["observation_profile"] == "rgb-notifications-v1"
        self.notifications = ""
        self.action_deadline_reached = lambda: False
        self.advanced_tics = 0
        self.decisions = 0
        self.native_return = 0.0
        self.terminated = self.truncated = self.player_dead = False
        self.goal_progress = 0
        self.game = vzd.DoomGame()
        self.config = tempfile.TemporaryDirectory(prefix="vizdoom-session-")
        try:
            if not self.game.load_config(str(installed / "scenarios" / f"{scenario}.cfg")):
                raise ValueError("could not load the frozen ViZDoom scenario")
            self.game.set_doom_game_path(str(installed / "freedoom2.wad"))
            self.game.set_doom_config_path(str(Path(self.config.name) / "doom.ini"))
            self.game.set_seed(instance["seed"])
            self.game.set_mode(vzd.Mode.PLAYER)
            self.game.set_window_visible(False)
            self.game.set_sound_enabled(False)
            self.game.set_screen_format(vzd.ScreenFormat.RGB24)
            self.game.set_depth_buffer_enabled(False)
            self.game.set_automap_buffer_enabled(False)
            self.game.set_labels_buffer_enabled(False)
            self.game.set_objects_info_enabled(False)
            self.game.set_sectors_info_enabled(False)
            self.game.set_audio_buffer_enabled(False)
            self.game.set_notifications_buffer_enabled(self.expose_notifications)
            if not self.expose_notifications:
                self.game.set_notifications_buffer_size(0)
            self.game.init()
            if ([button.name for button in self.game.get_available_buttons()] != self.buttons or
                    self.game.get_episode_start_time() != instance["start_tic"] or
                    self.game.get_episode_timeout() != instance["timeout_tics"] or
                    self.game.get_episode_time() != instance["start_tic"] or self.game.get_ticrate() != 35 or
                    self.game.get_total_reward() != 0 or (self.goal_variable is not None and
                        self.game.get_game_variable(self.goal_variable) != 0)):
                raise ValueError("ViZDoom native initialization differs from the frozen scenario")
            self._capture()
            if self.image is None:
                raise ValueError("ViZDoom did not supply an initial frame")
        except BaseException:
            self.close()
            raise

    def _capture(self):
        state = self.game.get_state()
        if state is None:
            if not (self.terminated or self.truncated):
                raise ValueError("missing screen during an active ViZDoom episode")
            self.image = None
            return
        frame = state.screen_buffer
        if frame.shape != (240, 320, 3) or str(frame.dtype) != "uint8":
            raise ValueError("ViZDoom must supply an RGB24 320x240 screen")
        self.image = frame.copy()
        if self.expose_notifications and state.notifications_buffer:
            self.notifications = state.notifications_buffer

    def spec(self):
        spec = {"adapter_version": "1.0.0", "capabilities": self.instance["capabilities"],
                "screen_width": 320, "screen_height": 240,
                "episode_timeout_tics": self.instance["timeout_tics"]}
        if self.variable_tics:
            spec["default_tics"] = self.default_tics
            if self.delta_buttons:
                spec["action_schema"] = {"type": "string", "pattern": dense_pattern(self.binary_buttons),
                                         "max_length": 512}
                spec["binary_buttons"] = self.binary_buttons
                spec["delta_buttons"] = self.delta_buttons
            else:
                alternatives = "|".join(re.escape(action) for action in self.actions)
                spec["action_schema"] = {"type": "string", "pattern": rf"(?:{alternatives}){DURATION}"}
                spec["actions"] = self.actions
        else:
            spec["action_schema"] = {"type": "string", "enum": self.actions}
            spec["tics_per_decision"] = self.default_tics
        return spec

    def observe(self):
        if self.image is None:
            return {"frame_available": False}
        response = {"frame_available": True, "image_png_base64": png(self.image)}
        if self.expose_notifications:
            response["notifications"] = self.notifications
        return response

    def step(self, action):
        controls, _, duration = action.partition("@")
        requested = int(duration) if duration and self.variable_tics else self.default_tics
        buttons, _, delta = controls.partition("~")
        pressed = set(buttons.split("+"))
        deltas = dict(zip(self.delta_buttons, map(float, delta.split(",")))) if delta else {}
        vector = [deltas.get(button, int(button in pressed)) for button in self.buttons]
        if self.terminated or self.truncated:
            raise ValueError("ViZDoom episode is closed")
        self.decisions += 1
        reward = 0.0
        start = self.advanced_tics
        timeout = self.instance["timeout_tics"]
        planned = min(requested, timeout - start) if timeout else requested
        # Map exit can reset the native absolute clock to zero. Count each
        # processed tic while exposing only the final snapshot of the decision.
        for _ in range(planned):
            increment = self.game.make_action(vector, 1)
            reward += increment
            self.advanced_tics += 1
            done = self.game.is_episode_finished()
            self.truncated = done and self.game.is_episode_timeout_reached()
            self.player_dead = done and self.game.is_player_dead()
            if self.goal_variable is not None:
                progress = int(self.game.get_game_variable(self.goal_variable))
                self.goal_progress = max(self.goal_progress, progress)
            elif self.goal == "correct-target" and increment > 0:
                # The correct target is the only positive reward event in this WAD.
                self.goal_progress = 1
            self.terminated = done and (not self.truncated or self.player_dead or self.success())
            if done:
                break
            if self.expose_notifications:
                state = self.game.get_state()
                if state.notifications_buffer:
                    self.notifications = state.notifications_buffer
            if self.game.get_episode_time() != self.instance["start_tic"] + self.advanced_tics:
                raise ValueError("ViZDoom tic accounting changed during an active episode")
            if self.action_deadline_reached():
                break
        if self.variable_tics:
            self.action_tics.append([requested, self.advanced_tics - start])
        self.native_return = self.game.get_total_reward()
        self._capture()
        return Transition(reward, self.terminated, self.truncated)

    def success(self):
        return self.goal is not None and self.goal_progress >= self.goal_value

    def metrics(self):
        metrics = self._native_metrics()
        if self.variable_tics:
            metrics["action_tics"] = self.action_tics
        return metrics

    def _native_metrics(self):
        metrics = {"native_return": self.native_return, "native_tics": self.advanced_tics,
                   "decisions": self.decisions, "native_terminated": self.terminated,
                   "native_truncated": self.truncated, "player_dead": self.player_dead}
        if self.goal is not None:
            metrics.update(objective_success=int(self.success()), objective_progress=self.goal_progress)
        metrics.update({variable.lower(): int(self.game.get_game_variable(getattr(vzd.GameVariable, variable)))
                        for variable in self.stats})
        return metrics

    def fingerprint(self):
        frame = hashlib.sha256(self.image.tobytes()).hexdigest() if self.image is not None else None
        state = {"screen_sha256": frame, "seed": self.instance["seed"], "metrics": self._native_metrics()}
        if self.expose_notifications:
            state["notifications"] = self.notifications
        return state_hash(state)

    def frame(self):
        return self.image

    def close(self):
        try:
            self.game.close()
        finally:
            self.config.cleanup()
