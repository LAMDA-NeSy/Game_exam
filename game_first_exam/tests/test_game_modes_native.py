"""New execution modes replay the same frozen native environments as their standard twins."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
BENCH=os.environ['GAME_TEST_BENCHMARK']
sys.path[:0]=[str(ROOT/'game_first_exam/runtime/modes'),str(ROOT/'game_first_exam/runtime'),str(ROOT/'scripts'),str(ROOT/'game_first_exam/benchmarks'/BENCH)]
from game_schemas import register_schemas
register_schemas()
from adapter import Adapter
from metric_rules import validate_metrics
from mode_grade import replay
from server import Game
from realtime_server import Realtime

class NativeModes(unittest.TestCase):
    def test_native_mode(self):
        if BENCH=='minihack':
            from privileged import Session
            task=ROOT/'game_first_exam/tasks/minihack/minihack-room-i01-privileged'
            instance_path=task/'tests/instance.json'
            session=Session(instance_path,task/'environment/sim')
            try:
                initial=session.adapter.fingerprint()
                self.assertEqual(len(session.observe()['observation']['chars']),21)
                self.assertEqual(set(session.spec()['observation_fields']),set(session.observe()['observation']))
                self.assertEqual(session.spec()['observation_profile'],'native-full-observation-v1')
                session.step('SE');session.reset()
                self.assertEqual(session.actions,[]);self.assertEqual(initial,session.adapter.fingerprint())
                for action in json.loads((task/'solution/actions.json').read_text()):session.step(action)
                with tempfile.TemporaryDirectory() as tmp:
                    path=Path(tmp)/'actions.json';session.save(path)
                    # Poison the agent's local state after exporting: the verifier must ignore it.
                    session.adapter.total_return=-999
                    result=replay(json.loads(instance_path.read_text()),json.loads((task/'tests/mode.json').read_text()),path,Path(tmp)/'verifier',Adapter,validate_metrics)
                    self.assertEqual(result['primary_score'],100);self.assertEqual(result['graded_by_live'],0)
                    self.assertTrue((Path(tmp)/'verifier/replay.mp4').is_file())
            finally:session.close()
        else:
            task=ROOT/'game_first_exam/tasks/crafter/crafter-survival-i01-realtime'
            instance=json.loads((task/'tests/instance.json').read_text());mode=json.loads((task/'tests/mode.json').read_text())
            with tempfile.TemporaryDirectory() as tmp:
                rt=Realtime(Game.open(Adapter,instance,task/'environment/sim',tmp),mode)
                try:
                    actions=json.loads((task/'solution/actions.json').read_text())
                    rt.submit({'actions':actions,'at':None,'request_id':'reference'})
                    for _ in actions:rt.tick(rt.next_tick)
                    self.assertTrue(rt.game.adapter.success());self.assertEqual(rt.game.steps,len(actions))
                    rt.tick(rt.next_tick)
                    self.assertEqual(rt.held_steps,1)
                finally:rt.seal()

if __name__=='__main__':unittest.main()
