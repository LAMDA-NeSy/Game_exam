"""The upstream default selection stays distinct from its extra native level."""
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from prepare_games import load_suite

class VMageSuiteSelection(unittest.TestCase):
    def test_default_extra_and_smoke_coverage(self):
        default,dp=load_suite('vmage');extra,ep=load_suite('vmage-extra');smoke,sp=load_suite('vmage-smoke')
        self.assertEqual(len(dp),33);self.assertEqual(len(ep),1);self.assertEqual(len(sp),5)
        self.assertEqual(set(ep),{'vmage-tempestrun-l05-i01-standard'})
        self.assertFalse(set(dp)&set(ep));self.assertTrue(set(sp)<=set(dp))
        self.assertIn('vmage-supermario-l00-i01-standard',dp)
        self.assertEqual(len(set(dp)|set(ep)),34)

    def test_default_order_and_tasks_match_frozen_native_inventory(self):
        suite,plans=load_suite('vmage')
        names=[r['name'] for r in suite['tasks']]
        expected=[]
        for game,levels in [('flappybird',range(1,8)),('supermario',[1,2,3,4,5,6,7,8,9,0]),('pong',range(1,4)),('race',range(1,10)),('tempestrun',range(1,5))]:
            expected.extend(f'vmage-{game}-l{level:02}-i01-standard' for level in levels)
        self.assertEqual(names,expected)
        self.assertEqual(len(names),len(set(names)))
        self.assertFalse(any('no-history' in n or 'no_history' in n for n in names))
        self.assertEqual({r['benchmark'] for r in suite['tasks']},{'vmage_race','vmage_flappybird','vmage_pong','vmage_supermario','vmage_tempestrun'})

if __name__=='__main__':unittest.main()
