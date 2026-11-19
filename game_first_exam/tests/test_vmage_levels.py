"""Frozen all-level coverage and independent native-run equivalence."""
import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import test_vmage_native as native

ROOT=native.ROOT
EXPECTED={'race':set(range(1,10)),'flappybird':set(range(1,8)),'pong':set(range(1,4)),'supermario':set(range(10)),'tempestrun':set(range(1,6))}

class VMageLevels(unittest.TestCase):
    def tasks(self):
        return sorted((ROOT/'game_first_exam/tasks/vmage').glob('vmage-*-standard'))

    def test_complete_native_level_inventory(self):
        rows=[json.loads((p/'tests/instance.json').read_text()) for p in self.tasks()]
        self.assertEqual(len(rows),34)
        actual={g:{r['native_level'] for r in rows if r['native_game']==g} for g in EXPECTED}
        self.assertEqual(actual,EXPECTED)
        limits={r['native_level']:r['native_frame_limit'] for r in rows if r['native_game']=='race'}
        self.assertEqual(limits,{1:100,2:150,3:150,4:150,5:150,6:100,7:100,8:300,9:500})
        limits={r['native_level']:r['native_frame_limit'] for r in rows if r['native_game']=='supermario'}
        self.assertEqual(limits,{0:5000,1:400,2:1000,3:1000,4:1000,5:300,6:300,7:300,8:1000,9:1000})
        for r in rows:
            self.assertEqual(r['family'],f'l{r["native_level"]:02}')
            self.assertIsNone(r['max_steps'])

    def test_stdlib_validation_rejects_mixed_level_bindings(self):
        sys.path.insert(0,str(native.RUNTIME));native.register_schemas()
        from config_schema import validate_instance
        for task in self.tasks():
            instance=json.loads((task/'tests/instance.json').read_text())
            with self.subTest(task=task.name):
                validate_instance(instance)
                for field,value in [('native_level',99),('native_level',True),('native_actions',['UNFROZEN']),('native_level_sha256','0'*64),('native_frame_limit',1),('seed',1),('adapter_version','2.0.0')]:
                    wrong=copy.deepcopy(instance);wrong[field]=value
                    with self.assertRaises(ValueError):validate_instance(wrong)

    def test_all_frozen_reference_traces_match_unmodified_native_loop(self):
        helper=native.VMageNative()
        results=[]
        for task in self.tasks():
            instance=json.loads((task/'tests/instance.json').read_text())
            game=instance['native_game'];level=instance['native_level']
            actions=json.loads((task/'solution/actions.json').read_text())
            # The full L0 map makes repeated purity/audit hashing slower under 1 CPU.
            # This is a unittest subprocess guard, not an episode wall-clock budget.
            guard='180' if game=='supermario' and level==0 else '90'
            with self.subTest(task=task.name),patch.dict(os.environ,{'VMAGE_TEST_LEVEL':str(level),'VMAGE_TEST_PROCESS_TIMEOUT':guard}):
                upstream=helper.run_episode('native',game,actions)
                bridge=helper.run_episode('bridge',game,actions)
                self.assertEqual(bridge['constructed'],1)
                self.assertEqual(bridge['initial'],upstream['initial'])
                self.assertEqual(len(bridge['calls']),len(upstream['calls']))
                cosmetic=game=='tempestrun' and upstream['final']['over']
                for a,b in zip(bridge['calls'],upstream['calls']):
                    for field in ['action','dt','result','state']:self.assertEqual(a[field],b[field],task.name+': '+field)
                    # Native Tempest death visuals depend on wall time; physics and RNG still match.
                    if not cosmetic or not b['state']['over']:self.assertEqual(a['pixels'],b['pixels'])
                self.assertEqual(bridge['final'],upstream['final'])
                if not cosmetic:
                    self.assertEqual(bridge['pixels'],upstream['pixels'])
                    self.assertEqual(bridge['frame_pixels'],upstream['pixels'])
                    self.assertEqual(bridge['observation'],upstream['observation'])
                results.append(dict(task=task.name,score=upstream['final']['score'],steps=len(bridge['transitions']),terminated=bridge['transitions'][-1]['terminated'] if bridge['transitions'] else False,truncated=bridge['transitions'][-1]['truncated'] if bridge['transitions'] else False,native_calls=len(upstream['calls']),cosmetic_death_pixels_excluded=bool(cosmetic)))
                print('native-equivalent',task.name,results[-1]['score'],results[-1]['steps'],flush=True)
        output=os.environ.get('VMAGE_LEVEL_RESULTS')
        if output:Path(output).write_text(json.dumps(results,indent=2)+'\n')

if __name__=='__main__':unittest.main()
