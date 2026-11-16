"""Local native environment access. Only saved actions cross the verifier boundary."""
import json
from pathlib import Path
from config_schema import validate_instance


class Session:
    def __init__(self, instance='/app/instance.json', assets='/app/assets'):
        from adapter import Adapter
        self.factory = Adapter
        self.instance = validate_instance(json.loads(Path(instance).read_text()))
        self.assets = Path(assets)
        self.adapter = None
        self.reset()

    @property
    def env(self):
        """The actual local Gymnasium environment; privileged code may inspect it."""
        return self.adapter.env

    def reset(self):
        self.close()
        self.adapter = self.factory(self.instance, self.assets)
        if self.adapter.fingerprint() != self.instance['initial_state_sha256']:
            self.close()
            raise ValueError('frozen initial state mismatch')
        self.actions = []
        self.done = False
        return self.observe()

    def spec(self):
        # The local privileged view is wider than the standard adapter's filtered view.
        fields = list(self.adapter.obs)
        return {**self.adapter.spec(), 'execution_mode': 'privileged',
                'observation_profile': 'native-full-observation-v1',
                'observation_fields': fields, 'local_reset': True,
                'observation': 'Complete native MiniHack arrays serialized as JSON lists. Fields are '
                               + ', '.join(fields) + '.'}

    def observe(self):
        # MiniHack exposes its complete native observation here, unlike the standard crop.
        observation = {k: v.tolist() if hasattr(v, 'tolist') else v for k, v in self.adapter.obs.items()}
        return {'step': len(self.actions), 'done': self.done, 'observation': observation}

    def step(self, action):
        if self.done or action not in self.spec()['action_schema']['enum']:
            raise ValueError('closed episode or invalid action')
        transition = self.adapter.step(action)
        self.actions.append(action)
        self.done = transition.terminated or transition.truncated
        return self.observe()

    def save(self, path='/app/output/actions.json'):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({'schema': 'game-actions/1.0', 'actions': self.actions}) + '\n')

    def close(self):
        if self.adapter is not None:
            self.adapter.close()
            self.adapter = None
