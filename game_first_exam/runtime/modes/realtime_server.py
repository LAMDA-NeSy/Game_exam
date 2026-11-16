"""Discrete-action realtime scheduler around the unchanged native Adapter and Game.

Commands are single-use native actions. Missing commands execute the declared native
noop, as upstream realtime holds discrete commands rather than repeating them.
"""
import copy
import json
import os
from pathlib import Path
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from mode_config import validate_mode, mode_hash
from server import Game

PROTOCOL = 'game-realtime/1.0'


class Realtime:
    def __init__(self, game, mode):
        self.game = game
        self.mode = validate_mode(mode)
        self.interval = float(mode['tick_seconds'])
        self.allowed = game.spec()['action_schema']['enum']
        if mode['idle_action'] not in self.allowed:
            raise ValueError('idle action is not a native action')
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.plan, self.requests = {}, {}
        self.next_tick = None
        self.clock_started = self.clock_stopped = None
        self.held_steps = self.late_steps = 0
        self.max_lag_s = self.stalled_s = 0.0
        self.thread = threading.Thread(target=self.run, daemon=True)

    def first_request(self):
        # Match upstream realtime.first_request(): the request budget starts before
        # motion. Reuse Game's budget/termination machinery, not another deadline.
        with self.lock:
            if self.game.started is None and self.game.final is None:
                self.game.start()
                self.game.recorder.event({'event': 'first_request', 'utc_s': time.time()})

    def check_time(self):
        self.game.check_time()
        if self.game.final is not None and self.clock_started is not None and self.clock_stopped is None:
            self.clock_stopped = time.monotonic()

    def clocks(self):
        now = time.monotonic()
        elapsed = 0.0 if self.game.started is None else now - self.game.started
        if self.game.final is not None:
            elapsed = self.game.final['elapsed_seconds']
        preparation = elapsed if self.clock_started is None else self.clock_started - self.game.started
        motion = 0.0 if self.clock_started is None else (self.clock_stopped if self.clock_stopped is not None else now) - self.clock_started
        return {'time_s': elapsed, 'time_left_s': max(0.0, self.game.wall_clock-elapsed),
                'preparation_s': preparation, 'clock_s': motion}

    def spec(self):
        self.first_request()
        return {**self.game.spec(), 'protocol': PROTOCOL, 'timing': {
            'realtime': True, 'wall_s_per_control_step': self.interval,
            'idle_action': self.mode['idle_action'], 'max_plan_steps': self.mode['max_plan_steps'],
            'starts_on': 'first accepted submit', 'missing_plan': 'native noop',
            'budget_clock': 'first request; Harbor session deadline remains authoritative'}}

    def snapshot(self, observation=True):
        # Reading starts the request budget, never the simulation clock or RNG.
        self.first_request()
        self.check_time()
        result = {'step': self.game.steps, 'done': self.game.final is not None,
                  'running': self.next_tick is not None and self.game.final is None,
                  'planned_steps': len(self.plan), **self.clocks()}
        if observation:
            result['observation'] = copy.deepcopy(self.game._observation)
        return result

    def submit(self, body):
        self.first_request()
        if not isinstance(body, dict) or set(body) != {'actions', 'at', 'request_id'}:
            raise ValueError('require actions, at and request_id')
        actions, at, rid = body['actions'], body['at'], body['request_id']
        if not isinstance(actions, list) or not 1 <= len(actions) <= self.mode['max_plan_steps']:
            raise ValueError('invalid plan length')
        if any(not isinstance(a,str) or a not in self.allowed for a in actions):
            raise ValueError('unknown native action')
        if at is not None and (type(at) is not int or at < 1):
            raise ValueError('at must be a positive tick or null')
        if not isinstance(rid,str) or not 1 <= len(rid) <= 80:
            raise ValueError('invalid request_id')
        with self.lock:
            if rid in self.requests:
                previous, result = self.requests[rid]
                if previous != body: raise ValueError('request_id reused with different payload')
                return copy.deepcopy(result)
            self.check_time()
            if self.game.final is not None: raise ValueError('episode closed')
            start = self.game.steps+1 if at is None else at
            if start > self.game.steps+self.mode['max_plan_steps'] or start+len(actions)-1 > self.game.steps+self.mode['max_plan_steps']:
                raise ValueError('plan too far ahead')
            late = min(len(actions), max(0, self.game.steps+1-start))
            remaining = actions[late:]; start += late
            if not remaining: raise ValueError('entire plan is late; observe and resubmit')
            self.plan = {n:a for n,a in self.plan.items() if n < start}
            self.plan.update({start+i:action for i,action in enumerate(remaining)})
            self.late_steps += late
            if self.next_tick is None:
                self.clock_started = time.monotonic()
                self.next_tick = self.clock_started+self.interval
                self.game.recorder.event({'event': 'clock_start', 'utc_s': time.time(), **self.clocks()})
            self.game.recorder.event({'event':'realtime_submit', 'request_id':rid, 'at':start, 'late_steps':late, 'actions':remaining})
            result = {**self.snapshot(), 'start_step':start, 'late_steps':late, 'plan_end_step':start+len(remaining)-1}
            self.requests[rid] = (copy.deepcopy(body), copy.deepcopy(result))
            return result

    def tick(self, now=None):
        with self.lock:
            now = time.monotonic() if now is None else now
            if self.next_tick is None or self.game.final is not None or now < self.next_tick: return False
            lag = max(0, now-self.next_tick); self.max_lag_s = max(self.max_lag_s,lag)
            if lag > .5:
                self.stalled_s += lag; self.next_tick = now
            index = self.game.steps+1
            held = index not in self.plan
            action = self.plan.pop(index,self.mode['idle_action'])
            try:
                self.game.submit({'action':action,'expected_step':self.game.steps,'request_id':'tick-'+str(index)})
                self.held_steps += int(held)
                self.game.recorder.event({'event':'realtime_tick','step':index,'wall_monotonic':now,'held':held})
            except Exception:
                # Game already seals adapter faults. A budget cutoff is a normal end.
                if self.game.final is None: raise
            self.next_tick += self.interval
            if self.game.final is not None:
                self.plan.clear()
                self.check_time()
            return True

    def run(self):
        while not self.stop_event.wait(.005):
            try:
                self.tick()
                with self.lock: self.check_time()
            except Exception as exc:
                with self.lock: self.game.fault(exc,'realtime_clock')
                return

    def seal(self):
        self.stop_event.set()
        with self.lock:
            if self.game.final is None: self.game.finalize('agent_finished')
            self.check_time()
            self.game.close()
            audit = {'protocol':PROTOCOL,'mode_sha256':mode_hash(self.mode),'executed_ticks':self.game.steps,
                     'held_steps':self.held_steps,'late_steps':self.late_steps,'max_lag_s':self.max_lag_s,'stalled_s':self.stalled_s,
                     'budget_clock': 'first_request', **self.clocks()}
            (self.game.output/'realtime.json').write_text(json.dumps(audit,indent=2)+'\n')
            (self.game.output/'collection.ready').touch()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def setup(self):
        super().setup(); self.connection.settimeout(5)
    def reply(self, code, data):
        payload=json.dumps(data,allow_nan=False).encode()
        self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
    def do_GET(self):
        rt=self.server.runtime
        rt.first_request()
        with rt.lock:
            if self.path=='/spec': result=rt.spec()
            elif self.path in {'/observe','/status'}: result=rt.snapshot(self.path=='/observe')
            else: result=None
        # A slow reader must never hold the simulator lock.
        self.reply(404,{'error':'unknown endpoint'}) if result is None else self.reply(200,result)
    def do_POST(self):
        self.server.runtime.first_request()
        if self.path!='/submit': return self.reply(404,{'error':'unknown endpoint'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 16384: raise ValueError('body must be 1..16384 bytes')
            result=self.server.runtime.submit(json.loads(self.rfile.read(length)))
            self.reply(200,result)
        except (ValueError,TypeError) as exc: self.reply(400,{'error_category':'invalid_request','error':str(exc)})


def main():
    from adapter import Adapter
    instance=json.loads(Path('/srv/instance.json').read_text())
    mode=json.loads(Path('/srv/mode.json').read_text())
    game=Game.open(Adapter,instance,Path('/srv'),Path('/data'),float(os.environ.get('RCB_WALL_CLOCK_S','600')))
    rt=Realtime(game,mode)
    (game.output/'server.pid').write_text(str(os.getpid()))
    http=ThreadingHTTPServer(('0.0.0.0',8000),Handler);http.runtime=rt
    signal.signal(signal.SIGUSR1,lambda *_: rt.seal())
    def stop(*_):
        rt.seal();raise SystemExit(0)
    signal.signal(signal.SIGTERM,stop)
    rt.thread.start()
    http.serve_forever()


if __name__=='__main__': main()
