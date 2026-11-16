"""The public checkout contains games and their shared dependencies only."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'ci_checks')]
import files_image
import task_conventions as tc


class LayoutTests(unittest.TestCase):
    def test_game_task_discovery_without_robot_sources(self):
        for benchmark, name in (
            ('MiniHack', 'minihack-room-i01-standard'),
            ('Crafter', 'crafter-survival-i01-realtime'),
        ):
            with self.subTest(benchmark=benchmark):
                task = tc.task_dir(name)
                self.assertTrue((task / 'task.toml').is_file())
                self.assertIn(task, tc.iter_tasks())
                self.assertEqual(task.parent, tc.bench_root(benchmark))
                self.assertEqual(ROOT / tc.task_relpath(name), task)
        self.assertTrue(tc.task_dir('minihack-room-i01-standard').is_relative_to(ROOT / 'game_first_exam/tasks'))
        self.assertFalse((ROOT / 'embodied_first_exam').exists())
        self.assertFalse((ROOT / 'tasks').exists())
        self.assertFalse((ROOT / 'website').exists())
        self.assertEqual(len(tc.iter_tasks()), len(set(tc.iter_tasks())))
        self.assertEqual(tc.check_layout(), [])

    def test_explicit_external_task_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task = root / 'minihack/minihack-room-i01-standard'
            task.mkdir(parents=True)
            (task / 'task.toml').write_text('')
            self.assertEqual(tc.task_dir(task.name, root), task)
            self.assertEqual(tc.iter_tasks(root), [task])

    def test_game_and_shared_images_resolve_without_duplicates(self):
        manifests = files_image.manifests()
        self.assertEqual(len({path.parent.name for path in manifests}), len(manifests))
        for name, parent in [('game-files', 'game_first_exam/images'), ('connection-files', 'images'), ('monitor', 'images')]:
            self.assertEqual(files_image.image_dir(name), ROOT / parent / name)
        self.assertIn(files_image.image_dir('game-files') / 'FILES.json', manifests)


if __name__ == '__main__':
    unittest.main()
