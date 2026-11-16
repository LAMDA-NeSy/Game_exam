"""Game readiness against live HTTP and lost action replies."""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'shared/connection'), str(ROOT / 'game_first_exam/runtime'),
               str(ROOT / 'game_first_exam/tests')]
from game_client import GameClient
from server import Game, Handler
from service_connection import NotReady, ReadinessTimeout, service_urls, wait_for_ready
from test_game_service import Backend, instance


class Clock:
    now = 0.0
    def time(self): return self.now
    def sleep(self, delay): self.now += delay


class ConnectionTests(unittest.TestCase):
    def server(self, handler, game=False):
        server = HTTPServer(('127.0.0.1', 0), handler)
        if game:
            directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
            server.game = Game(Backend(), instance(), directory.name)
            self.addCleanup(server.game.close)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        thread.start()
        def close():
            server.shutdown(); server.server_close(); thread.join(timeout=2)
        self.addCleanup(close)
        return server, f'http://127.0.0.1:{server.server_port}'

    def responder(self, status, body, headers=None):
        class Reply(BaseHTTPRequestHandler):
            calls = 0
            def log_message(self, *_): pass
            def do_GET(self):
                type(self).calls += 1
                payload = json.dumps(body).encode()
                self.send_response(status)
                self.send_header('Content-Length', str(len(payload)))
                for k, v in (headers or {}).items(): self.send_header(k, v)
                self.end_headers(); self.wfile.write(payload)
        _, url = self.server(Reply)
        return Reply, url

    def test_explicit_addresses_are_pinned_and_defaults_deduplicated(self):
        self.assertEqual(service_urls('http://a:1/', 'http://b:2'), ('http://a:1',))
        self.assertEqual(service_urls(configured='http://b:2'), ('http://b:2',))
        self.assertEqual(service_urls(), ('http://sim:8000', 'http://localhost:8000'))
        for url in ['', 'file:///tmp/server', 'http://a?url=b', 'http://user:password@a']:
            with self.subTest(url=url), self.assertRaises(ValueError): service_urls(url)

    def test_game_agent_needs_only_two_stdlib_client_files(self):
        _, base = self.server(Handler, game=True)
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copyfile(ROOT / 'game_first_exam/runtime/game_client.py', Path(tmp) / 'game_client.py')
            shutil.copyfile(ROOT / 'shared/connection/service_connection.py', Path(tmp) / 'service_connection.py')
            code = 'from game_client import GameClient; import sys; assert GameClient(sys.argv[1]).wait_ready()["protocol"] == "game-standard/2.2"'
            subprocess.run([sys.executable, '-S', '-c', code, base], cwd=tmp, check=True, capture_output=True, text=True)

    def test_deadline_and_warming_address_are_shared_policy(self):
        clock = Clock(); calls = []
        def warming(url, remaining):
            calls.append((url, remaining)); raise NotReady('warming', responding=True)
        with self.assertRaises(ReadinessTimeout):
            wait_for_ready(('a', 'b'), warming, timeout=.25, interval=.1, clock=clock.time, sleep=clock.sleep)
        self.assertEqual([c[0] for c in calls], ['a', 'a', 'a'])
        self.assertAlmostEqual(clock.now, .25)
        self.assertTrue(all(0 < remaining <= .25 for _, remaining in calls))
        with self.assertRaisesRegex(ValueError, 'protocol'):
            wait_for_ready(('a', 'b'), lambda *_: (_ for _ in ()).throw(ValueError('protocol')), timeout=1)

    def test_delayed_socket_start_and_spec_probes_do_not_advance_game(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        server = HTTPServer(('127.0.0.1', 0), Handler, bind_and_activate=False)
        server.server_bind()
        server.game = Game(Backend(), instance(), directory.name); self.addCleanup(server.game.close)
        active = threading.Event()
        def run():
            active.wait(); server.server_activate(); server.serve_forever(poll_interval=.01)
        thread = threading.Thread(target=run, daemon=True); thread.start()
        timer = threading.Timer(.08, active.set); timer.start()
        try:
            client = GameClient(f'http://127.0.0.1:{server.server_address[1]}', startup_timeout=2, poll_interval=.01)
            before = server.game.adapter.fingerprint()
            client.wait_ready()
            self.assertEqual(server.game.steps, 0)
            self.assertIsNone(server.game.started)
            self.assertEqual(before, server.game.adapter.fingerprint())
        finally:
            timer.join(); active.set(); server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_default_fallback_occurs_only_before_selection(self):
        server, base = self.server(Handler, game=True)
        unused = socket.socket(); unused.bind(('127.0.0.1', 0)); bad = f'http://127.0.0.1:{unused.getsockname()[1]}'
        self.addCleanup(unused.close)  # Bound but not listening: refuses a connection.
        with patch('service_connection.DEFAULT_URLS', (bad, base)), patch.dict(os.environ, {}, clear=True):
            client = GameClient(startup_timeout=.5, poll_interval=.01)
            client.wait_ready(); self.assertEqual(client.url, base)
            with self.assertRaises(ReadinessTimeout):
                GameClient(bad, startup_timeout=.03, poll_interval=.01).wait_ready()
            self.assertEqual(server.game.steps, 0)

    def test_503_waits_but_does_not_probe_another_game(self):
        class Warm(Handler):
            probes = 0
            def do_GET(self):
                type(self).probes += 1
                if self.path == '/spec' and self.probes < 3:
                    self.reply(503, {'error': 'warming'}); return
                super().do_GET()
        server, base = self.server(Warm, game=True)
        backup, other = self.responder(200, {'protocol': 'game-standard/2.2'})
        with patch('service_connection.DEFAULT_URLS', (base, other)), patch.dict(os.environ, {}, clear=True):
            client = GameClient(startup_timeout=1, poll_interval=.01); client.wait_ready()
        self.assertEqual(backup.calls, 0); self.assertEqual(server.game.steps, 0)
        self.assertEqual(client._urls, (base,))

    def test_wrong_protocol_terminal_fault_and_redirect_fail_immediately(self):
        for status, body in [(200, {'protocol': 'eai-standard/2.2'}), (409, {'error': 'ended'}),
                             (500, {'error_category': 'environment'}), (200, [])]:
            handler, base = self.responder(status, body)
            with self.subTest(status=status), self.assertRaises(ValueError):
                GameClient(base, startup_timeout=1, poll_interval=.01).wait_ready()
            self.assertEqual(handler.calls, 1)
        backup, other = self.responder(200, {'protocol': 'game-standard/2.2'})
        _, base = self.responder(302, {}, {'Location': other + '/spec'})
        with self.assertRaises(ValueError): GameClient(base).wait_ready()
        self.assertEqual(backup.calls, 0)

    def test_lost_action_reply_is_not_retried_and_same_id_deduplicates(self):
        class LoseReply(Handler):
            posts: ClassVar[list] = []
            drop = True
            def do_POST(self):
                if type(self).drop:
                    body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    type(self).posts.append(body)
                    self.server.game.submit(body)
                    type(self).drop = False
                    self.connection.shutdown(socket.SHUT_RDWR); self.close_connection = True
                    return
                type(self).posts.append('normal')
                super().do_POST()
        server, base = self.server(LoseReply, game=True)
        backup, other = self.responder(200, {'protocol': 'game-standard/2.2'})
        with patch('service_connection.DEFAULT_URLS', (base, other)), patch.dict(os.environ, {}, clear=True):
            client = GameClient(startup_timeout=1, poll_interval=.01)
            with self.assertRaises(ConnectionError): client.step('forward', 0, request_id='one')
            self.assertEqual(len(LoseReply.posts), 1)
            self.assertEqual((server.game.steps, server.game.adapter.position), (1, 1))
            client.wait_ready()
            reply = client.step('forward', 0, request_id='one')
            self.assertEqual(reply['step'], 1); self.assertEqual(server.game.steps, 1)
            with self.assertRaises(ValueError): client.step('noop', 0, request_id='one')
            with self.assertRaises(ValueError): client.step('forward', 0, request_id='different')
            done = client.step('forward', 1, request_id='two')
            self.assertTrue(done['done']); self.assertEqual(server.game.steps, 2)
            client.wait_ready()  # A readable terminal service does not create a new episode.
            with self.assertRaises(ValueError): client.step('noop', 2, request_id='after-end')
        self.assertEqual(backup.calls, 0)
        self.assertEqual(server.game.steps, 2)


if __name__ == "__main__":
    unittest.main()
