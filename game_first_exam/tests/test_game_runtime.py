"""Capture actual runtime image identity without collecting container secrets."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from game_runtime import (
    RuntimeCapture,
    frozen_instance_metadata,
    project_trial,
    report_code_metadata,
    validate_report_code,
)


class RuntimeTests(unittest.TestCase):
    def test_historical_results_cannot_silently_use_changed_scoring_code(self):
        snapshot = {'report_code_sha256': report_code_metadata()}
        validate_report_code(snapshot)
        snapshot['report_code_sha256']['game_first_exam/runtime/reducers.py'] = 'changed'
        with self.assertRaises(ValueError): validate_report_code(snapshot)
        with self.assertRaises(ValueError): validate_report_code({})

    def test_indirect_classification_dependencies_are_frozen(self):
        snapshot = {'report_code_sha256': report_code_metadata()}
        for name in ('scripts/account_failure_check.py', 'scripts/retry_policy.py',
                     'scripts/game_runtime.py', 'game_first_exam/runtime/config_schema.py'):
            with self.subTest(name=name):
                self.assertIn(name, snapshot['report_code_sha256'])
                changed = {**snapshot['report_code_sha256'], name: 'changed'}
                with patch('game_runtime.report_code_metadata', return_value=changed), self.assertRaises(ValueError):
                    validate_report_code(snapshot)

    def test_complete_instance_is_frozen_and_detached(self):
        import hashlib
        instance = {'engine_commit': 'abc', 'native_max_steps': 100, 'future_field': {'values': [1]}}
        record = frozen_instance_metadata(instance)
        instance['future_field']['values'].append(2)
        self.assertEqual(record['instance']['future_field']['values'], [1])
        encoded = json.dumps(record['instance'], sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(record['instance_sha256'], hashlib.sha256(encoded).hexdigest())

    def test_project_selection_does_not_capture_other_jobs(self):
        self.assertEqual(project_trial('a__xyz__env', ['A__xYz']), 'A__xYz')
        self.assertEqual(project_trial('a__xyz__verifier__trial', ['A__xYz']), 'A__xYz')
        self.assertIsNone(project_trial('a__xyz-other__env', ['A__xYz']))
        self.assertIsNone(project_trial('another__env', ['A__xYz']))

    def test_privileged_coverage_has_no_sim_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            job=Path(tmp);trial=job/'room__abc';trial.mkdir()
            (trial/'config.json').write_text('{}')
            (trial/'lock.json').write_text(json.dumps({'task':{'name':'minihack-room-i01-privileged'}}))
            capture=RuntimeCapture(job)
            for i,(project,service) in enumerate([('room__abc__env','main'),('room__abc__env','rcb_monitor'),('room__abc__verifier__trial','main')]):
                capture.records[str(i)]={'trial':trial.name,'project':project,'service':service}
            capture.stop.set();capture.thread.start();capture.thread.join()
            self.assertTrue(capture.finish()['complete'])

    def test_actual_image_hash_and_caps_are_captured_but_env_is_never_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = Path(tmp); trial = job / 'task__ABC'; trial.mkdir(); (trial / 'config.json').write_text('{}')
            capture = RuntimeCapture(job)
            calls = []
            def fake(argv):
                calls.append(argv)
                if argv[1] == 'ps':
                    return json.dumps({'ID': 'id', 'Labels': 'com.docker.compose.project=task__abc__env,com.docker.compose.service=sim'})
                if argv[1] == 'inspect': return json.dumps(['id', 'sha256:actual', 'local-tag', 1024, 1000000000, 128])
                if argv[1:3] == ['image', 'inspect']: return json.dumps([[], 'linux', 'arm64'])
                raise AssertionError(argv)
            with patch('game_runtime.command', fake): capture.sample()
            data = capture.records['id']
            self.assertEqual(data['image_id'], 'sha256:actual')
            self.assertEqual(data['architecture'], 'arm64')
            self.assertEqual(data['memory_bytes'], 1024)
            self.assertFalse(any('.Config.Env' in str(c) for c in calls))
            self.assertEqual(set(data), {'trial','project','service','container_id','image_id','configured_image',
                'repo_digests','os','architecture','memory_bytes','nano_cpus','pids_limit'})
            # Missing short-lived containers are disclosed, not inferred from a tag.
            capture.stop.set(); capture.thread.start(); capture.thread.join()
            result = capture.finish()
            self.assertFalse(result['complete'])
            saved = json.loads((job / 'runtime-images.json').read_text())
            self.assertEqual(len(saved['coverage']['task__ABC']['missing_roles']), 3)


if __name__ == '__main__':
    unittest.main()
