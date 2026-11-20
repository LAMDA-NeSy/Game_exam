"""Trusted host registry and extra native runtime binding regressions; no game engines required."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'game_first_exam/runtime')]
import files_image
import game_schemas
import task_conventions as tc
from game_preflight import validate_task


class RegistryTests(unittest.TestCase):
    def registry(self, text, root):
        registry = root / 'registry.toml'
        registry.write_text(text)
        with patch.object(game_schemas, 'ROOT', root), patch.object(game_schemas, 'REGISTRY', registry):
            return game_schemas.registrations()

    def test_schema_only_rows_keep_their_existing_runtime_bindings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = self.registry('[benchmarks.example]\nschema="game_first_exam/benchmarks/example/instance_schema.py"', root)
            self.assertEqual(rows['example']['runtime_files'], {})
            self.assertEqual(rows['example']['schema'], root / 'game_first_exam/benchmarks/example/instance_schema.py')
            self.assertEqual(rows['example']['adapter'], root / 'game_first_exam/benchmarks/example/adapter.py')
            self.assertEqual(rows['example']['metric_rules'], root / 'game_first_exam/benchmarks/example/metric_rules.py')

    def test_registry_rejects_unknown_fields_and_untrusted_paths(self):
        schema = 'schema="game_first_exam/benchmarks/example/instance_schema.py"\n'
        invalid = [
            'unknown=true\n[benchmarks.example]\n' + schema,
            '[benchmarks.example]\n' + schema + 'unexpected=true',
            '[benchmarks.example]\nruntime_files={}',
            '[benchmarks.example]\nschema=123',
            '[benchmarks.example]\nschema="/tmp/instance_schema.py"',
            '[benchmarks.example]\nschema="game_first_exam/benchmarks/../runtime/instance_schema.py"',
            '[benchmarks.example]\n' + schema + 'runtime_files=[]',
            '[benchmarks.example]\n' + schema + 'adapter="/tmp/adapter.py"',
            '[benchmarks.example]\n' + schema + 'adapter="game_first_exam/benchmarks/example/not_adapter.py"',
            '[benchmarks.example]\n' + schema + 'metric_rules="scripts/metric_rules.py"',
            '[benchmarks.example]\n' + schema + 'metric_rules="game_first_exam/benchmarks/example/unknown.py"',
        ]
        for target, source in [
            ('/app/helper.py', 'game_first_exam/benchmarks/common/helper.py'),
            ('/srv', 'game_first_exam/benchmarks/common/helper.py'),
            ('/srv/../app/helper.py', 'game_first_exam/benchmarks/common/helper.py'),
            ('/srv//helper.py', 'game_first_exam/benchmarks/common/helper.py'),
            ('/srv/helper.py', '/tmp/helper.py'),
            ('/srv/helper.py', 'scripts/helper.py'),
            ('/srv/helper.py', 'game_first_exam/benchmarks/../runtime/helper.py'),
        ]:
            invalid.append('[benchmarks.example]\n' + schema + f'runtime_files={{"{target}"="{source}"}}')
        with tempfile.TemporaryDirectory() as tmp:
            for text in invalid:
                with self.subTest(registry=text), self.assertRaises(ValueError):
                    self.registry(text, Path(tmp))

    def test_source_symlink_cannot_leave_trusted_benchmarks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            benchmarks = root / 'game_first_exam/benchmarks'
            benchmarks.mkdir(parents=True)
            (root / 'untrusted').mkdir()
            (benchmarks / 'example').symlink_to(root / 'untrusted', target_is_directory=True)
            with self.assertRaises(ValueError):
                self.registry('[benchmarks.example]\nschema="game_first_exam/benchmarks/example/instance_schema.py"', root)

    def test_vmage_has_five_separate_schemas_under_one_task_root(self):
        rows = game_schemas.registrations()
        for game in ('race', 'flappybird', 'pong', 'supermario', 'tempestrun'):
            benchmark = 'vmage_' + game
            with self.subTest(benchmark=benchmark):
                self.assertEqual(rows[benchmark]['schema'], ROOT / f'game_first_exam/benchmarks/vmage/{game}/instance_schema.py')
                self.assertEqual(rows[benchmark]['adapter'], ROOT / f'game_first_exam/benchmarks/vmage/{game}/adapter.py')
                self.assertEqual(rows[benchmark]['metric_rules'], ROOT / f'game_first_exam/benchmarks/vmage/{game}/metric_rules.py')
                self.assertEqual(rows[benchmark]['runtime_files'], {
                    '/srv/' + filename: ROOT / 'game_first_exam/benchmarks/vmage/common' / filename
                    for filename in ('vmage_bridge.py', 'source_loader.py', 'SOURCE.json')
                })
                name = f'vmage-{game}-l01-i01-standard'
                self.assertEqual(tc.task_dir(name), ROOT / f'game_first_exam/tasks/vmage/{name}')

    def test_native_test_lock_matches_the_runtime_baseline(self):
        self.assertEqual((ROOT / 'game_first_exam/benchmarks/vmage/common/requirements.txt').read_text(),
                         (ROOT / 'game_first_exam/tests/envs/locks/vmage.txt').read_text())

    def test_preflight_rejects_missing_or_stale_extra_runtime_bindings(self):
        # Reuse an existing frozen task so this exercises the complete Docker COPY inspection.
        import tomllib
        suite = tomllib.loads((ROOT / 'configs/game_suites/minigrid.toml').read_text())
        row = suite['tasks'][0]
        source = ROOT / 'game_first_exam/benchmarks/minigrid/adapter.py'
        original = files_image.copied_from
        for copied_source in (None, ROOT / 'game_first_exam/benchmarks/crafter/adapter.py', source):
            def copied(path):
                bindings, errors = original(path)
                if Path(path).parent.name == 'sim' and copied_source is not None:
                    bindings['/srv/native_helper.py'] = copied_source
                return bindings, errors
            with self.subTest(source=copied_source), \
                    patch('game_preflight.runtime_files', return_value={'/srv/native_helper.py': source}), \
                    patch('files_image.copied_from', side_effect=copied):
                if copied_source == source:
                    validate_task(row)
                else:
                    with self.assertRaisesRegex(ValueError, 'missing/stale public service binding'):
                        validate_task(row)

    def test_extra_runtime_files_cannot_override_core_service_bindings(self):
        import tomllib
        row = tomllib.loads((ROOT / 'configs/game_suites/minigrid.toml').read_text())['tasks'][0]
        with patch('game_preflight.runtime_files', return_value={'/srv/server.py': Path('/tmp/evil.py')}), \
                self.assertRaisesRegex(ValueError, 'runtime binding conflicts'):
            validate_task(row)


if __name__ == '__main__':
    unittest.main()
