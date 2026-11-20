"""Native Harbor configuration/lock integration; requires the pinned Harbor package, no Docker or model."""

import asyncio
import contextlib
import io
import json
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from harbor.cli.main import app as harbor_app
from harbor.models.job.config import JobConfig
from harbor.publisher.packager import Packager
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from game_harbor import GameRecords
from game_reports import aggregate, write_harbor_report
from game_runtime import report_code_metadata
from prepare_games import load_suite, prepare, select_tasks
import efe
import run_games


class GameSelection(unittest.TestCase):
    def test_game_only_default_and_all_selection_never_launches(self):
        for flags, expected in ((["--list", "--standard"], 30),
                                (["--all", "--standard", "--list"], 53)):
            with self.subTest(flags=flags), contextlib.redirect_stdout(io.StringIO()) as output, \
                    patch("efe.harbor") as launch, patch("efe.prepull") as pull:
                self.assertEqual(efe.run(flags), 0)
            names = output.getvalue().splitlines()
            self.assertEqual(len(names), expected)
            self.assertTrue(all(name.startswith(("minigrid-", "crafter-", "textworld-", "babaisai-", "minihack-", "vizdoom-"))
                                for name in names))
            launch.assert_not_called()
            pull.assert_not_called()

    def test_vizdoom_mixed_objective_and_native_score_reporting(self):
        _, plans = load_suite("vizdoom")
        self.assertEqual(len(plans), 11)
        records = {}
        trials = []
        for name, (_, _, instance) in plans.items():
            records[name] = {key: instance[key] for key in ("benchmark", "family", "seed", "metric_spec")}
            records[name]["digest"] = "sha256:fixture"
            primary = instance["metric_spec"]["primary"]
            value = 1 if primary == "objective_success" else 1000
            trials.append({"task": name, "valid": True, "success": int(primary == "objective_success"),
                           "status": "success" if primary == "objective_success" else "fail",
                           "native_metrics": {primary: value}, "steps": 1})
        output = aggregate(trials, records)["benchmarks"]["vizdoom"]
        self.assertEqual((output["valid"], output["completion_valid"], output["scored_valid"]), (11, 5, 6))
        self.assertEqual(output["success_rate"], 1)
        self.assertEqual(output["macro_primary_score"], 1)
        self.assertEqual(output["families"]["deathmatch"]["mean_primary_score"], 1000)
        self.assertEqual(sum(row["status"] == "scored" and row["success"] is None for row in trials), 6)
        self.assertEqual(aggregate([], records)["benchmarks"]["vizdoom"]["missing"], 11)

    def test_checkout_discovery_works_without_upstream_task_tree(self):
        self.assertTrue(efe.is_tree(ROOT))
        self.assertFalse((ROOT / "tasks").exists())
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(efe.is_tree(Path(tmp)))


    def test_legacy_entry_passes_other_native_agents_without_codex_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv = [
                "run_games.py",
                "--suite",
                "minihack",
                "--family",
                "room",
                "--mode",
                "standard",
                "--agent",
                "claude-code",
                "--model",
                "anthropic/test-model",
                "--ak",
                "max_turns=3",
                "--jobs-dir",
                tmp,
                "--name",
                "claude-config",
            ]
            with patch.object(sys, "argv", argv), patch("run_games.subprocess.run") as launch:
                launch.return_value.returncode = 7
                self.assertEqual(run_games.main(), 7)
            command = launch.call_args.args[0]
            self.assertIn("--standard", command)
            native = self.native_config(["-c", command[command.index("-c") + 1], "--ak", "max_turns=3"])
            self.assertEqual(native.agents[0].name, "claude-code")
            self.assertEqual(native.agents[0].model_name, "anthropic/test-model")
            self.assertEqual(native.agents[0].kwargs, {"max_turns": 3})

    def test_legacy_entry_rejects_unimplemented_mode_before_launch(self):
        with (
            patch.object(sys, "argv", ["run_games.py", "--suite", "minihack", "--mode", "realtime"]),
            patch("run_games.subprocess.run") as launch,
            self.assertRaises(SystemExit) as error,
        ):
            run_games.main()
        self.assertEqual(error.exception.code, 2)
        launch.assert_not_called()

    def test_shared_filters_and_listing_do_not_prepare_or_run(self):
        output = io.StringIO()
        with (
            contextlib.redirect_stdout(output),
            patch("efe.prepull") as pull,
            patch("prepare_games.prepare") as stage,
            patch("efe.harbor") as launch,
        ):
            code = efe.run(
                [
                    "--game-suite=minihack-balrog",
                    "--benchmark",
                    "MiniHack",
                    "--standard",
                    "-p",
                    str(ROOT / "game_first_exam/tasks/minihack"),
                    "-i",
                    "minihack-quest-*",
                    "-x",
                    "*-medium-*",
                    "-l",
                    "1",
                    "--list",
                ]
            )
        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue().strip(), "minihack-quest-easy-i01-standard")
        pull.assert_not_called()
        stage.assert_not_called()
        launch.assert_not_called()

    def test_empty_conflicting_and_unknown_game_selection_fail_closed(self):
        for flags in (
            ["--all"],
            ["--core"],
            ["--family", "missing"],
            ["--realtime"],
            ["-i", "robotwin*"],
            ["--game-suite", "core"],
        ):
            with self.subTest(flags=flags), patch("efe.harbor") as launch:
                self.assertEqual(efe.run(["--game-suite", "minihack-balrog", "--list", *flags]), 2)
                launch.assert_not_called()

    def native_config(self, argv):
        app = getattr(harbor_app, "__wrapped_app__", harbor_app)
        result = CliRunner().invoke(app, ["run", *argv, "--print-config"])
        self.assertEqual(result.exit_code, 0, result.output)
        return JobConfig.model_validate_json(result.stdout)

    def test_unified_selection_passes_profiles_to_native_harbor(self):
        with tempfile.TemporaryDirectory() as tmp:

            def stage(suite, plans, selected, output):
                return prepare(suite, plans, selected, Path(tmp) / "tasks.json")

            for profile in ("oracle", "nop", "codex-deepseek"):
                # The task set is prepared once; all profiles resolve through Harbor's real CLI.
                profile_path = ROOT / "configs/harbor" / f"{profile}.json"
                with (
                    self.subTest(profile=profile),
                    patch("efe.prepull"),
                    patch("prepare_games.files_image.build"),
                    patch("prepare_games.prepare", side_effect=stage),
                    patch("efe.harbor", side_effect=lambda argv, app: self.native_config(argv[1:])),
                ):
                    resolved = efe.run(["--game-suite", "minihack", "--standard", "--family", "room", "-c", str(profile_path)])
                expected = JobConfig.model_validate_json(profile_path.read_text())
                self.assertEqual(resolved.agents, expected.agents)
                self.assertEqual([t.path.name for t in resolved.tasks], ["minihack-room-i01-standard"])
                self.assertEqual(resolved.n_concurrent_trials, 1)
                self.assertEqual(resolved.retry.max_retries, 0)
                shutil.rmtree(Path(tmp) / "tasks.tasks")
                (Path(tmp) / "tasks.json").unlink()

    def test_native_agent_flag_replaces_policy_and_profiles_append(self):
        profile = str(ROOT / "configs/harbor/codex-deepseek.json")
        cfg = self.native_config(["-c", profile, "-a", "codex", "-m", "replacement-model"])
        self.assertEqual(cfg.agents[0].model_name, "replacement-model")
        self.assertNotIn("web_search", cfg.agents[0].kwargs)
        doubled = self.native_config(["-c", profile, "-c", str(ROOT / "configs/harbor/oracle.json")])
        self.assertEqual(len(doubled.agents), 2)

    def test_plain_native_source_is_still_passed_through(self):
        argv = ["-c", "own-job.json", "--print-config"]
        with patch("efe.prepull"), patch("efe.harbor", return_value=0) as launch:
            self.assertEqual(efe.run(argv), 0)
        launch.assert_called_once_with(["run", *argv], None)

    def test_legacy_model_override_preserves_native_tool_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv = [
                "run_games.py",
                "--suite",
                "minihack",
                "--family",
                "room",
                "--agent",
                "codex",
                "--model",
                "replacement-model",
                "--agent-version",
                "0.167.1",
                "--name",
                "compat",
                "--jobs-dir",
                tmp,
            ]
            with patch.object(sys, "argv", argv), patch("run_games.subprocess.run") as launch:
                launch.return_value.returncode = 7  # Stop at dispatch; never call a paid model in this test.
                self.assertEqual(run_games.main(), 7)
            command = launch.call_args.args[0]
            self.assertIn("--game-suite", command)
            self.assertNotIn("-a", command)
            cfg = self.native_config(["-c", command[command.index("-c") + 1]])
            self.assertEqual(cfg.agents[0].model_name, "replacement-model")
            baseline = JobConfig.model_validate_json((ROOT / "configs/harbor/codex-deepseek.json").read_text())
            self.assertEqual(cfg.agents[0].kwargs, baseline.agents[0].kwargs)


class HarborIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.suite, self.plans = load_suite("minihack")
        self.selected = [row for row in select_tasks(self.suite, families=["room"]) if row["name"].endswith("-standard")]
        with patch("prepare_games.files_image.build"):
            self.config_path = prepare(self.suite, self.plans, self.selected, self.root / "run.json")
        self.config = JobConfig.model_validate_json(self.config_path.read_text())
        self.config.agents[0].name = "oracle"
        self.job = self.root / "job"
        self.job.mkdir()
        self.task = self.config.tasks[0].path
        self.digest = "sha256:" + Packager.compute_content_hash(self.task)[0]
        self.task_lock = {"name": self.task.name, "type": "local", "path": str(self.task), "digest": self.digest}
        self.trial_lock = {"task": self.task_lock, "agent": {"name": "oracle", "model_name": None}}
        (self.job / "lock.json").write_text(json.dumps({"trials": [self.trial_lock]}))
        (self.job / "config.json").write_text(self.config.model_dump_json())
        (self.job / "result.json").write_text('{"native_harbor_result": true}')
        (self.job / "game-provenance.json").write_text(json.dumps({"report_code_sha256": report_code_metadata()}))

    def tearDown(self):
        self.tmp.cleanup()

    def add_trial(self, success=1):
        trial = self.job / "room__trial"
        (trial / "artifacts/data").mkdir(parents=True)
        (trial / "lock.json").write_text(json.dumps(self.trial_lock))
        (trial / "result.json").write_text(
            json.dumps(
                {
                    "task_name": self.task.name,
                    "verifier_result": {
                        "rewards": {"success": success, "steps": 4, "return": float(success), "infra_error": 0}
                    },
                }
            )
        )
        (trial / "artifacts/data/final.json").write_text(json.dumps({"metrics": {"completion_score": 100 * success}}))
        return trial

    def test_prepared_config_is_native_and_does_not_overwrite_task_sources(self):
        self.assertEqual(len(self.config.tasks), 1)
        self.assertEqual(self.config.retry.max_retries, 0)
        self.assertEqual(self.config.n_attempts, 1)
        self.assertNotEqual(self.task, self.plans[self.task.name][0])
        self.assertEqual(self.digest, (self.task / "DIGEST").read_text().strip())
        with self.assertRaises(ValueError):
            prepare(self.suite, self.plans, self.selected, self.config_path)
        self.assertFalse(list(self.root.rglob("suite-snapshot.json")))

    def test_native_records_are_not_replaced_and_missing_trials_stay_missing(self):
        originals = {name: (self.job / name).read_bytes() for name in ("config.json", "lock.json", "result.json")}
        summary = write_harbor_report(self.job)
        self.assertFalse(summary["complete"])
        self.assertIsNone(summary["benchmarks"]["minihack"]["macro_primary_score"])
        self.add_trial()
        summary = write_harbor_report(self.job)
        self.assertTrue(summary["complete"])
        self.assertEqual(summary["benchmarks"]["minihack"]["macro_primary_score"], 100)
        for name, content in originals.items():
            self.assertEqual((self.job / name).read_bytes(), content)
        self.assertTrue((self.job / "game-report/REPORT.md").is_file())
        self.assertFalse((self.job / "suite-snapshot.json").exists())

    def test_changed_task_or_trial_binding_is_rejected(self):
        trial = self.add_trial()
        modified = {**self.trial_lock, "task": {**self.task_lock, "digest": "sha256:" + "0" * 64}}
        (trial / "lock.json").write_text(json.dumps(modified))
        with self.assertRaisesRegex(ValueError, "trial task differs"):
            write_harbor_report(self.job)
        (trial / "lock.json").write_text(json.dumps(self.trial_lock))
        with (self.task / "instruction.md").open("a") as stream:
            stream.write("\nmodified after run\n")
        with self.assertRaisesRegex(ValueError, "contents differ"):
            write_harbor_report(self.job)

    def test_duplicates_and_changed_report_code_cannot_rewrite_scores(self):
        trial = self.add_trial()
        shutil.copytree(trial, self.job / "room__second")
        with self.assertRaisesRegex(ValueError, "multiple attempts"):
            write_harbor_report(self.job)
        shutil.rmtree(self.job / "room__second")
        with patch("game_runtime.report_code_metadata", return_value={}):
            with self.assertRaisesRegex(ValueError, "implementation differs"):
                write_harbor_report(self.job)

    def test_plugin_preflight_and_error_status(self):
        (self.job / "game-provenance.json").unlink()
        job = SimpleNamespace(config=self.config, job_dir=self.job)
        plugin = GameRecords()
        with (
            patch("game_harbor.runner_metadata", return_value={"harbor_version": "native", "interaction_policy": {}}),
            patch("game_harbor.RuntimeCapture") as capture,
        ):
            asyncio.run(plugin.on_job_start(job))
            capture.return_value.start.assert_called_once()
            capture.return_value.finish.return_value = {"complete": False}
            with patch("game_harbor.write_harbor_report", side_effect=ValueError("bad evidence")):
                with self.assertRaises(ValueError):
                    asyncio.run(plugin.on_job_end(None))
        saved = json.loads((self.job / "game-provenance.json").read_text())
        self.assertEqual(saved["status"], "report_error")
        self.assertNotIn("harbor_version", saved["runtime"])

    def test_plugin_rejects_mixed_execution_modes(self):
        alternate = self.config.tasks[0].model_copy(deep=True)
        alternate.path = ROOT / "game_first_exam/tasks/minihack/minihack-room-i01-privileged"
        self.config.tasks.append(alternate)
        job = SimpleNamespace(config=self.config, job_dir=self.job)
        with self.assertRaisesRegex(ValueError, "one execution mode"):
            asyncio.run(GameRecords().on_job_start(job))

    def test_plugin_rejects_multiple_attempt_protocol_before_start(self):
        self.config.n_attempts = 2
        job = SimpleNamespace(config=self.config, job_dir=self.job)
        with self.assertRaisesRegex(ValueError, "one agent, one attempt"):
            asyncio.run(GameRecords().on_job_start(job))


if __name__ == "__main__":
    unittest.main()
