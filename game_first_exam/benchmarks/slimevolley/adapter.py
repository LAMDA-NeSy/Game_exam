"""Native SlimeVolley pixel play against the built-in left-side policy."""

from importlib.metadata import version

from slimevolleygym.slimevolley import SlimeVolleyAtariEnv
from contracts import Capabilities, Transition
from encoding import png, state_hash

ACTIONS = ("idle", "left", "left_jump", "jump", "right_jump", "right")


class Adapter:
    def __init__(self, instance, assets=None):
        for package, expected in instance["engine_versions"].items():
            if version(package) != expected:
                raise ValueError(f"SlimeVolley dependency version mismatch: {package}")
        self.env = SlimeVolleyAtariEnv()
        if self.env.t_limit != instance["native_max_steps"] or self.env.action_space.n != len(ACTIONS):
            raise ValueError("SlimeVolley native limits or actions changed")
        self.env.seed(instance["seed"])
        self.image = self.env.reset()
        self.ended = False

    def spec(self):
        return {
            "adapter_version": "1.0.0",
            "capabilities": Capabilities(images=True, action_mode="enum", native_truncation=True).to_dict(),
            "action_schema": {"type": "string", "enum": list(ACTIONS)},
            "observation": "Native 168×84 RGB frame from the right player's match.",
        }

    def observe(self):
        return {"image_png_base64": png(self.image)}

    def step(self, action):
        if self.ended:
            raise ValueError("episode closed")
        self.image, reward, self.ended, info = self.env.step(ACTIONS.index(action))
        terminated = min(info["ale.lives"], info["ale.otherLives"]) == 0
        return Transition(float(reward), terminated, bool(self.ended and not terminated))

    def success(self):
        game = self.env.game
        return self.ended and game.agent_right.life > game.agent_left.life

    def metrics(self):
        game = self.env.game
        right, left = game.agent_right.life, game.agent_left.life
        return {"native_return": right - left, "right_lives": right, "left_lives": left,
                "points_for": 5 - left, "points_against": 5 - right, "native_steps": self.env.t}

    def fingerprint(self):
        game = self.env.game
        players = [vars(player) | {"state": vars(player.state)}
                   for player in (game.agent_right, game.agent_left)]
        return state_hash({
            "players": players, "ball": vars(game.ball), "delay": game.delayScreen.life,
            "opponent_rnn": self.env.policy.outputState, "steps": self.env.t,
            "rng": game.np_random.bit_generator.state,
        })

    def frame(self):
        return self.image

    def close(self):
        self.env.close()
