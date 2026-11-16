"""Replay trust boundaries and real-clock behavior, independent of paid agents."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'game_first_exam/tests'),str(ROOT/'game_first_exam/runtime/modes')]
from test_game_service import Backend, instance, Game
from mode_config import validate_mode
from mode_grade import replay
from realtime_server import Realtime

MODE={'mode':'realtime','version':'1.1.0','tick_seconds':.02,'idle_action':'noop','max_plan_steps':16}

class Modes(unittest.TestCase):
    def runtime(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        cfg=instance();cfg['max_steps']=None
        rt=Realtime(Game(Backend(),cfg,temp.name),MODE)
        self.addCleanup(rt.seal)
        return rt

    def test_clock_paused_until_submit_then_advances_without_requests(self):
        rt=self.runtime();rt.thread.start()
        before=rt.game.adapter.fingerprint();rt.snapshot();rt.spec();time.sleep(.04)
        self.assertEqual(rt.game.steps,0);self.assertEqual(rt.game.adapter.fingerprint(),before)
        rt.submit({'actions':['noop'],'at':None,'request_id':'first'})
        deadline=time.monotonic()+1
        while rt.game.steps<3 and time.monotonic()<deadline:time.sleep(.01)
        with rt.lock:
            self.assertGreaterEqual(rt.game.steps,3)
            self.assertGreaterEqual(rt.held_steps,2)

    def test_queued_native_actions_end_successfully_and_reading_is_pure(self):
        rt=self.runtime();rt.submit({'actions':['forward','forward'],'at':None,'request_id':'plan'})
        rt.tick(rt.next_tick);rt.tick(rt.next_tick)
        self.assertTrue(rt.game.final['success']);self.assertEqual(rt.game.steps,2)
        state=rt.game.adapter.fingerprint();rt.snapshot();rt.spec()
        self.assertEqual(state,rt.game.adapter.fingerprint())
        with self.assertRaises(ValueError):rt.submit({'actions':['noop'],'at':None,'request_id':'after'})

    def test_request_replay_never_requeues_actions_and_partial_lateness(self):
        rt=self.runtime();body={'actions':['noop'],'at':None,'request_id':'once'}
        first=rt.submit(body);rt.tick(rt.next_tick)
        self.assertEqual(rt.submit(body),first);self.assertEqual(rt.plan,{})
        with self.assertRaises(ValueError):rt.submit({**body,'actions':['forward']})
        result=rt.submit({'actions':['noop','forward'],'at':1,'request_id':'late'})
        self.assertEqual(result['late_steps'],1);self.assertEqual(rt.plan,{2:'forward'})

    def test_bad_commands_do_not_start_or_advance_clock(self):
        rt=self.runtime()
        for body in [{'actions':['invalid'],'at':None,'request_id':'a'}, {'actions':['noop'],'at':True,'request_id':'b'}, {'actions':['noop']*17,'at':None,'request_id':'c'}]:
            with self.assertRaises(ValueError):rt.submit(body)
        self.assertIsNone(rt.next_tick);self.assertEqual(rt.game.steps,0)

    def test_request_budget_counts_preparation_without_advancing_world(self):
        rt=self.runtime(); initial=rt.game.adapter.fingerprint()
        with patch('realtime_server.time.monotonic', return_value=100):
            rt.spec()
        with patch('realtime_server.time.monotonic', return_value=160):
            obs=rt.snapshot()
            self.assertEqual(obs['time_s'],60)
            self.assertEqual(obs['time_left_s'],rt.game.wall_clock-60)
            self.assertEqual(obs['clock_s'],0)
            self.assertEqual(obs['preparation_s'],60)
            self.assertEqual(obs['step'],0);self.assertFalse(obs['running'])
            self.assertEqual(rt.game.adapter.fingerprint(),initial)
            reply=rt.submit({'actions':['noop'],'at':None,'request_id':'start'})
            self.assertEqual(reply['time_left_s'],obs['time_left_s'])
        with patch('realtime_server.time.monotonic', return_value=161):
            self.assertEqual(rt.snapshot()['clock_s'],1)
            self.assertEqual(rt.snapshot()['preparation_s'],60)
            rt.seal()
            timing=json.loads((rt.game.output/'realtime.json').read_text())
            self.assertEqual(timing['preparation_s'],60)
            self.assertEqual(timing['clock_s'],1)

    def test_preparation_can_exhaust_budget_before_any_action(self):
        rt=self.runtime()
        with patch('realtime_server.time.monotonic', return_value=100):rt.spec()
        with patch('realtime_server.time.monotonic', return_value=101+rt.game.wall_clock):
            rt.check_time()
            self.assertTrue(rt.snapshot()['done'])
            self.assertEqual(rt.snapshot()['time_left_s'],0)
            self.assertEqual(rt.snapshot()['clock_s'],0)
            self.assertEqual(rt.game.steps,0)
            self.assertEqual(rt.game.final['reason'],'time_limit')
            with self.assertRaises(ValueError):rt.submit({'actions':['noop'],'at':None,'request_id':'late'})

    def test_service_start_without_requests_spends_no_budget(self):
        rt=self.runtime();rt.check_time()
        self.assertIsNone(rt.game.started)
        self.assertIsNone(rt.game.final)

    def test_replay_reconstructs_environment_and_rejects_forged_submission(self):
        mode={'mode':'privileged','version':'1.0.0','max_actions':4}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'actions.json'
            src.write_text(json.dumps({'schema':'game-actions/1.0','actions':['forward','forward']}))
            instances=[]
            def factory(*_):
                backend=Backend();instances.append(backend);return backend
            result=replay(instance(),mode,src,root/'good',factory,lambda *_:None)
            self.assertEqual(result['success'],1);self.assertEqual(result['graded_by_live'],0)
            self.assertEqual(result['replays'],1);self.assertTrue(instances[0].closed)
            src.write_text(json.dumps({'schema':'game-actions/1.0','actions':[],'success':True}))
            result=replay(instance(),mode,src,root/'forged',factory,lambda *_:None)
            self.assertEqual(result['success'],0);self.assertEqual(result['infra_error'],0)
            self.assertEqual(len(instances),2)

    def test_replay_engine_fault_is_not_valid_model_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'actions.json';src.write_text('{"schema":"game-actions/1.0","actions":[]}')
            def factory(*_):raise RuntimeError('engine unavailable')
            result=replay(instance(),{'mode':'privileged','version':'1.0.0','max_actions':4},src,Path(tmp)/'run',factory,lambda *_:None)
            self.assertEqual(result['infra_error'],1);self.assertFalse(result['result_valid'])

    def test_realtime_collection_freezes_sim_before_slow_monitor(self):
        sys.path.insert(0, str(ROOT/'images/monitor'))
        from rcb_monitor.inject import render_toml
        task=ROOT/'game_first_exam/tasks/crafter/crafter-survival-i01-realtime/task.toml'
        import tomllib
        first=render_toml(task.read_text())
        # Re-normalization must preserve the boundary, including during staging.
        for text in (first,render_toml(first)):
            hooks=tomllib.loads(text)['verifier']['collect']
            self.assertEqual([h['service'] for h in hooks if h['service']!='main'],['sim','rcb_monitor'])

    def test_terminated_trajectory_with_extra_actions_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'actions.json'
            src.write_text(json.dumps({'schema':'game-actions/1.0','actions':['forward','forward','noop']}))
            result=replay(instance(),{'mode':'privileged','version':'1.0.0','max_actions':4},src,Path(tmp)/'run',lambda *_:Backend(),lambda *_:None)
            self.assertEqual(result['reason'],'bad_trajectory')
            self.assertEqual(result['primary_score'],0)
            self.assertEqual(result['native_metrics']['completion_score'],0)
            self.assertEqual(result['success'],0)

    def test_mode_config_is_versioned_and_unknown_fields_rejected(self):
        validate_mode(MODE)
        for changes in [{'tick_seconds':0},{'version':'9'},{'idle_action':'forward'},{'extra':1}]:
            with self.assertRaises(ValueError):validate_mode({**MODE,**changes})

if __name__=='__main__':unittest.main()
