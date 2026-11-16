"""Protocol-neutral readiness polling extracted from the standard Robot client's strategy.

Only read-only probes belong here. Action requests must never be retried or rerouted.
This module has no simulator, reset, scoring, or crash-recovery policy.
"""
import math
import time
from urllib.parse import urlsplit

DEFAULT_URLS = ('http://sim:8000', 'http://localhost:8000')


class NotReady(ConnectionError):
    def __init__(self, message, *, responding=False):
        super().__init__(message)
        self.responding = responding


class ReadinessTimeout(RuntimeError):
    pass


def positive_seconds(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(name + ' must be finite and positive')
    return float(value)


def service_urls(explicit=None, configured=None):
    # A caller-selected URL is authoritative: never silently use a different episode.
    selected = explicit if explicit is not None else configured
    values = (selected,) if selected is not None else DEFAULT_URLS
    result = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError('service URL must be a string')
        url = value.strip().rstrip('/')
        parts = urlsplit(url)
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.query or parts.fragment or parts.username or parts.password:
            raise ValueError('invalid service URL')
        if url not in result:
            result.append(url)
    return tuple(result)


def wait_for_ready(urls, probe, *, timeout, interval=2.0, clock=time.monotonic, sleep=time.sleep):
    """probe(url, remaining_seconds) returns evidence or raises NotReady.

    Only NotReady is retryable. A responding/warming service pins the address;
    protocol errors and terminal responses propagate immediately. A probe must
    cap its network timeout to the supplied remaining budget.
    """
    timeout = positive_seconds(timeout, 'readiness timeout')
    interval = positive_seconds(interval, 'poll interval')
    candidates = tuple(dict.fromkeys(urls))
    if not candidates:
        raise ValueError('no service addresses')
    deadline = clock() + timeout
    last = None
    while clock() < deadline:
        for url in candidates:
            remaining = deadline - clock()
            if remaining <= 0:
                break
            try:
                result = probe(url, remaining)
                if clock() > deadline:
                    raise ReadinessTimeout('service answered after the readiness deadline')
                return url, result
            except NotReady as exc:
                last = exc
                if exc.responding:
                    candidates = (url,)
                    break
        remaining = deadline - clock()
        if remaining > 0:
            sleep(min(interval, remaining))
    raise ReadinessTimeout(f'service unavailable within {timeout:g}s; last probe: {last}')
