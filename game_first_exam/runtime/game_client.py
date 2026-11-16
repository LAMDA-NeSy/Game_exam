"""Public protocol client, with no engine, frozen instance, or grading implementation."""
import base64
import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from service_connection import NotReady, positive_seconds, service_urls, wait_for_ready

PROTOCOL = 'game-standard/2.2'


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GameClient:
    def __init__(self, url=None, *, startup_timeout=60.0, request_timeout=30.0, poll_interval=.25):
        self._urls = service_urls(url, os.environ.get('GAME_URL'))
        self.url = self._urls[0]
        self.startup_timeout = positive_seconds(startup_timeout, 'startup timeout')
        self.request_timeout = positive_seconds(request_timeout, 'request timeout')
        self.poll_interval = positive_seconds(poll_interval, 'poll interval')
        self._connected = False
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirects())

    def _probe(self, url, remaining):
        try:
            with self.opener.open(url + '/spec', timeout=min(self.request_timeout, remaining)) as response:
                spec = json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                if exc.code == 503:
                    self._urls = (url,)
                    self.url = url
                    raise NotReady('service warming up', responding=True) from exc
                raise ValueError(exc.read().decode()) from exc
            finally:
                exc.close()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            raise NotReady(type(exc).__name__) from exc
        if not isinstance(spec, dict) or spec.get('protocol') != PROTOCOL:
            raise ValueError('not a supported game service')
        return spec

    def wait_ready(self, timeout=None):
        # Once selected, never switch to another address, even after a lost response.
        urls = (self.url,) if self._connected else self._urls
        self.url, spec = wait_for_ready(urls, self._probe,
            timeout=self.startup_timeout if timeout is None else timeout, interval=self.poll_interval)
        self._connected = True
        return spec

    def request(self, path, body=None):
        if not self._connected:
            self.wait_ready()
        request = urllib.request.Request(self.url + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=self.request_timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                raise ValueError(exc.read().decode()) from exc
            finally:
                exc.close()

    def spec(self):
        return self.request("/spec")

    def observe(self):
        return self.request("/observe")

    def status(self):
        return self.request("/status")

    def step(self, action, expected_step, request_id=None):
        return self.request("/submit", {"action": action, "expected_step": expected_step,
                                        "request_id": request_id or str(uuid.uuid4())})

    act = step

    @staticmethod
    def save_image(response, path):
        observation = response.get("observation", response)
        encoded = observation.get("image_png_base64")
        if encoded is None:
            return False
        Path(path).write_bytes(base64.b64decode(encoded))
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("action", nargs="?", default="observe")
    parser.add_argument("--image", default="/app/output/view.png")
    args = parser.parse_args()
    client = GameClient()
    if args.action in {"spec", "status"}:
        result = getattr(client, args.action)()
    else:
        result = client.observe()
        if args.action != "observe":
            result = client.step(args.action, result["step"])
        client.save_image(result, args.image)
        result.get("observation", result).pop("image_png_base64", None)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
