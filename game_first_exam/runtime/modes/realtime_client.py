"""Game realtime transport; reuse the standard client's connection and request machinery."""
import json
import urllib.error
import uuid
from game_client import GameClient as StandardClient
from service_connection import NotReady

PROTOCOL = 'game-realtime/1.0'


class GameClient(StandardClient):
    def _probe(self, url, remaining):
        try:
            with self.opener.open(url + '/spec', timeout=min(self.request_timeout, remaining)) as response:
                spec = json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                if exc.code == 503:
                    self._urls, self.url = (url,), url
                    raise NotReady('service warming up', responding=True) from exc
                raise ValueError('realtime service rejected readiness probe') from exc
            finally:
                exc.close()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            raise NotReady(type(exc).__name__) from exc
        if not isinstance(spec, dict) or spec.get('protocol') != PROTOCOL:
            raise ValueError('not a supported realtime game service')
        return spec

    def submit(self, actions, *, at=None, request_id=None):
        return self.request('/submit', {'actions': actions, 'at': at, 'request_id': request_id or str(uuid.uuid4())})

    def step(self, action, expected_step=None, request_id=None):
        raise ValueError('realtime uses submit([actions], at=optional_tick), not synchronous step')

    act = step
