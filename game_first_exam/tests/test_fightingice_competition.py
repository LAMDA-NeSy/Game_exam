"""Focused tests for the separate archive-based competition prototype."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

BENCHMARK = Path(__file__).resolve().parents[1] / "benchmarks/fightingice"
sys.path.insert(0, str(BENCHMARK))
from competition import author_controller, load_model_profile, main, snapshot, stage_author
from competition_results import (
    SPEEDRUN_PROFILE, TRACKS, duel_report, duel_schedule, read_match, schedule,
    speedrun_report, summarize, verify_evidence,
)
from competition_match import relay
from competition_wire import packet, public_state, receive, send


class CompetitionTests(unittest.TestCase):
    def test_speedrun_model_uses_track_instructions_and_one_authoring_job(self):
        import tomllib

        profile = {"agents": [{"name": "oracle"}]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for track, style in (("rushdown", "close-range pressure"), ("zoning", "distance control")):
                character, baseline, _ = TRACKS[track]
                task = root / track
                stage_author(task, track=track, league="speedrun")
                prompt = (task / "instruction.md").read_text()
                for text in (character, baseline, style, "average scored frames", "4200 frames",
                             "does not provide audio or screen"):
                    self.assertIn(text, prompt)
                cfg = tomllib.loads((task / "task.toml").read_text())
                self.assertEqual(cfg["agent"]["timeout_sec"], 600)
                self.assertEqual(cfg["verifier"]["environment_mode"], "separate")
                self.assertEqual(cfg["verifier"]["network_mode"], "no-network")
                job = json.loads((task / "author-job.json").read_text())
                self.assertEqual((job["n_attempts"], job["retry"]["max_retries"]), (1, 0))
                argv = ["competition.py", "run", "--league", "speedrun", "--track", track,
                        "--model", "profile.json", "--release", "engine.zip", "--resources", "resources.zip",
                        "--output", str(task)]
                with patch.object(sys, "argv", argv), patch("competition.load_native_profile", return_value=profile), \
                        patch("competition.run_series") as run:
                    main()
                    args, output, rows, sources, profiles = run.call_args.args
                    self.assertEqual(args.track, track)
                    self.assertEqual(output, task)
                    self.assertEqual(rows, schedule(track, ["entry"], "speedrun"))
                    self.assertEqual(sources, {})
                    self.assertEqual(profiles, {"entry": profile})
                with patch.object(sys, "argv", [*argv, "another=/tmp/source"]), redirect_stderr(StringIO()), \
                        patch("competition.run_series") as run, self.assertRaises(SystemExit):
                    main()
                run.assert_not_called()

    def test_speedrun_schedule(self):
        for track, (character, baseline, _) in TRACKS.items():
            rows = schedule(track, ["alpha", "beta"], "speedrun")
            self.assertEqual(len(rows), 20)
            for entry in ("alpha", "beta"):
                for p1, p2 in ((entry, baseline), (baseline, entry)):
                    self.assertEqual([r["game"] for r in rows if (r["p1"], r["p2"]) == (p1, p2)],
                                     list(range(1, 6)))
            self.assertTrue(all(r["character"] == character for r in rows))

    def test_speedrun_scores_all_rounds_and_shares_rank(self):
        rows = schedule("rushdown", ["slow", "fast-tie", "fast"], "speedrun")
        results = []
        for match in rows:
            entry_is_p2 = match["p1"] == "MctsAi23i"
            name = match["p2"] if entry_is_p2 else match["p1"]
            points = [(1, 400, 0, 600 if name != "slow" else 3000),
                      (2, 100, 200, 50), (3, 50, 50, 3600)]
            if entry_is_p2:
                points = [(n, other, hp, frames) for n, hp, other, frames in points]
            results.append({"points": points})

        report = speedrun_report(rows, results)
        self.assertEqual(report["standings"], [
            {"rank": 1, "controllers": ["fast", "fast-tie"]}, {"rank": 3, "controllers": ["slow"]},
        ])
        fast = report["controllers"]["fast"]
        self.assertEqual((fast["games"], fast["rounds"], fast["wins"], fast["draws"], fast["losses"]),
                         (10, 30, 10, 10, 10))
        self.assertEqual((fast["penalty_rounds"], fast["average_frames"]), (10, 2800))
        self.assertAlmostEqual(fast["average_seconds"], 2800 / 60)
        swapped = report["matches"][-1]["rounds"]
        self.assertEqual(swapped[0], dict(round=1, p1_hp=0, p2_hp=400, elapsed_frames=600,
                                          scored_frames=600, outcome="win"))
        self.assertEqual((swapped[1]["elapsed_frames"], swapped[1]["scored_frames"]), (50, 4200))
        with self.assertRaisesRegex(ValueError, "incomplete speedrun match matrix"):
            speedrun_report(rows, results[:-1])
        with self.assertRaisesRegex(ValueError, "five matches on each side"):
            speedrun_report(rows[:-1], results[:-1])
        results[-1]["points"].pop()
        with self.assertRaisesRegex(ValueError, "incomplete speedrun rounds"):
            speedrun_report(rows, results)

    def test_speedrun_summarize_requires_frozen_schedule_and_verified_matches(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(sys, "argv", ["competition.py", "summarize", tmp]):
            output = Path(tmp)
            rows = schedule("zoning", ["entry"], "speedrun")
            (output / "provenance.json").write_text(json.dumps({
                "profile": SPEEDRUN_PROFILE, "track": "zoning", "baseline": "MctsAiZoning",
                "controller_sha256": {"entry": {}},
            }))
            matrix = output / "schedule.json"
            matrix.write_text(json.dumps(rows[:-1]))
            with self.assertRaisesRegex(ValueError, "stored match matrix"):
                main()
            matrix.write_text(json.dumps(rows))
            with self.assertRaisesRegex(ValueError, "0001: missing verified match"):
                main()
            (output / "0001").mkdir()
            (output / "0001/verified.json").write_text("{}")
            with patch("competition.verify_evidence", return_value={"points": []}):
                with self.assertRaisesRegex(ValueError, "0001: native CSV and verified result differ"):
                    main()

    def test_duel_schedule_and_score(self):
        rows = duel_schedule("rushdown", 2)
        self.assertEqual([(r["p1"], r["p2"], r["game"]) for r in rows], [
            ("model-a", "model-b", 1), ("model-b", "model-a", 1),
            ("model-a", "model-b", 2), ("model-b", "model-a", 2),
        ])
        for pairs in (0, -1, True):
            with self.assertRaises(ValueError):
                duel_schedule("rushdown", pairs)
        # The two controllers tie on points, but B has more remaining HP.
        points = [[1, 110, 0, 360], [2, 0, 0, 720], [3, 110, 110, 3600]]
        swapped = [[1, 200, 0, 360], [2, 0, 0, 720], [3, 200, 200, 3600]]
        style = [{f"P{side}_{col}": 0 for side in (1, 2)
                  for col in ("comboCount", "ProximityScore", "corneredFrames")}] * 3
        report = duel_report(rows[:2], [{"points": p, "style": style} for p in (points, swapped)], {})
        self.assertEqual([s["controllers"] for s in report["standings"]], [["model-b"], ["model-a"]])
        self.assertEqual(report["matches"][1]["round_points"], {"model-a": 1.0, "model-b": 2.0})
        self.assertFalse(report["audio"])
        with self.assertRaises(ValueError):
            duel_report(rows, [], {})

    def test_duel_harbor_profiles_and_failed_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "model.json"
            profile = {"agents": [{"name": "codex", "model_name": "example-model",
                                   "kwargs": {"version": "0.1", "reasoning_effort": "low"}}]}
            config.write_text(json.dumps(profile))
            self.assertEqual(load_model_profile(config), profile)
            for invalid in ({**profile, "tasks": [{}]}, {**profile, "n_attempts": 2}, {
                "agents": [{**profile["agents"][0], "override_timeout_sec": 900}]
            }, {"agents": profile["agents"] * 2}):
                config.write_text(json.dumps(invalid))
                with self.assertRaises(ValueError):
                    load_model_profile(config)
            task = root / "author"
            stage_author(task, track="zoning")
            prompt = (task / "instruction.md").read_text()
            self.assertIn("both sides as NEZ", prompt)
            self.assertIn("does not provide audio", prompt)
            jobs = root / "author-jobs"
            trial = jobs / "model-a/trial"
            trial.mkdir(parents=True)
            result = {"finished_at": "finished", "verifier_environment_mode": "separate",
                      "agent_info": {"name": "codex", "version": "0.1"},
                      "verifier_result": {"rewards": {"reward": 1.0}}, "exception_info": None}
            result_file = trial / "result.json"
            result_file.write_text(json.dumps(result))
            with patch("competition.subprocess.run") as run:
                path, model = author_controller("harbor", task, jobs, "model-a", profile)
                self.assertEqual(path, trial / "artifacts/app/output")
                self.assertEqual(model["model_name"], "example-model")
                self.assertEqual(model["reasoning_effort"], "low")
                self.assertIn("model-a", run.call_args.args[0])
                result["exception_info"] = {"type": "AgentTimeoutError"}
                result_file.write_text(json.dumps(result))
                with self.assertRaisesRegex(ValueError, "did not produce a verified controller"):
                    author_controller("harbor", task, jobs, "model-a", profile)

    def test_archive_schedule_sizes(self):
        entries = list("abcdefgh")
        for track in ("zoning", "rushdown"):
            standard = schedule(track, entries, "standard")
            self.assertEqual(len(standard), 90)  # 10 players, each pair switches sides.
            self.assertEqual(len(schedule(track, entries, "style")), 160)  # only entrants scored
            self.assertEqual(len(schedule(track, ["entry"], "style", mcts_only=True)), 10)
            self.assertEqual(sum(r["p1"] == "a" for r in standard), 9)
        for entries in (["a", "a"], ["../a"], ["organizer"], []):
            with self.assertRaises(ValueError):
                schedule("rushdown", entries, "style")

    def test_archive_style_and_standard_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            points, style = root / "points.csv", root / "style.csv"
            points.write_text("1,400,350,3600\n2,0,20,1000\n3,20,20,3600\n")
            style.write_text(
                "P1_ProjectileScore,P1_ProximityScore,P1_AntiAirCount,"
                "P2_ProjectileScore,P2_ProximityScore,P2_AntiAirCount\n"
                "69,-76,7,34,-76,3\n72,-76,10,36,-76,1\n66,-32,5,33,-32,6\n")
            result = read_match("zoning", points, style)
            match = schedule("zoning", ["entry"], "style", True)[0]
            totals = summarize([match], [result])["controllers"]["entry"]
            self.assertEqual((totals["round_points"], totals["remaining_hp"], totals["speed_frames"]),
                             (1.5, 420, 11400))
            self.assertEqual(totals["style"]["ProjectileScore"], 69)
            self.assertNotIn("standings", summarize([match], [result]))
            with self.assertRaises(ValueError):
                summarize([match], [])
            points.write_text("1,400,350,3600\n2,0,20,1000\n")
            with self.assertRaises(ValueError):
                read_match("zoning", points, style)

    def test_verifier_rejects_callback_disagreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("point", "style"):
                (root / "engine/log" / name).mkdir(parents=True)
            points = [[i, 400, 400, 3600] for i in range(1, 4)]
            (root / "engine/log/point/match.csv").write_text(
                "".join(",".join(map(str, row)) + "\n" for row in points))
            columns = [f"P{side}_{field}" for side in (1, 2)
                       for field in ("comboCount", "ProximityScore", "corneredFrames")]
            (root / "engine/log/style/match.csv").write_text(",".join(columns) + "\n" + "0,0,0,0,0,0\n" * 3)
            match = schedule("rushdown", ["entry"], "standard", True)[0]
            callback = {"callbacks": 10800, "controller_disconnected": False, "round_results": points}
            record = {"points": points, "style": [dict.fromkeys(columns, 0)] * 3, "callbacks": {"1": callback}}
            result_file = root / "match-result.json"
            result_file.write_text(json.dumps(record))
            totals = summarize([match], [verify_evidence(root, match)])
            self.assertEqual(totals["standings"], [{"rank": 1, "controllers": ["MctsAi23i", "entry"]}])
            callback["round_results"] = points[:2]
            result_file.write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                verify_evidence(root, match)

    def test_snapshot_rejects_symlink_and_harbor_task_is_artifact_only(self):
        import tomllib
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            controller = source / "controller.py"
            controller.write_text("class AI: pass\n")
            manifest = snapshot(source, root / "snapshot")
            self.assertEqual(list(manifest), ["controller.py"])
            (source / "not-a-submission").symlink_to(controller)
            with self.assertRaises(ValueError):
                snapshot(source, root / "unsafe")
            stage_author(root / "author")
            cfg = tomllib.loads((root / "author/task.toml").read_text())
            self.assertEqual(cfg["verifier"]["network_mode"], "no-network")
            self.assertEqual(cfg["artifacts"], ["/app/output/"])
            self.assertNotIn("competition_match", (root / "author/environment/Dockerfile").read_text())

    def test_packet_limit_and_no_privileged_state(self):
        from pyftg.models.enums.flag import Flag
        from pyftg.protoc.service_pb2 import PlayerGameState
        native = PlayerGameState(state_flag=Flag.PROCESSING.value, is_control=True)
        native.frame_data.current_frame_number = 6
        native.non_delay_frame_data.current_frame_number = 20
        native.screen_data.SetInParent()
        native.audio_data.SetInParent()
        flag, public = public_state(native)
        self.assertEqual(flag, Flag.PROCESSING)
        self.assertEqual(public.frame_data.current_frame_number, 6)
        self.assertFalse(public.HasField("non_delay_frame_data"))
        self.assertFalse(public.HasField("screen_data"))
        self.assertTrue(public.HasField("audio_data"))
        _, duel_public = public_state(native, audio=False)
        self.assertFalse(duel_public.HasField("audio_data"))
        self.assertTrue(duel_public.is_control)
        left, right = socket.socketpair()
        with left, right:
            send(left, public.SerializeToString())
            self.assertEqual(PlayerGameState.FromString(packet(right)), public)
            send(left, b"x" * 129)
            with self.assertRaises(ValueError):
                packet(right, 128)

    def test_relay_passes_native_events_and_returns_only_keys(self):
        from pyftg.models.enums.flag import Flag
        from pyftg.protoc.message_pb2 import GrpcKey
        from pyftg.protoc.service_pb2 import PlayerGameState

        engine, trusted_engine = socket.socketpair()
        player, trusted_player = socket.socketpair()
        with engine, trusted_engine, player, trusted_player, ThreadPoolExecutor() as pool:
            for sock in (engine, trusted_engine, player, trusted_player):
                sock.settimeout(2)
            future = pool.submit(relay, trusted_engine, trusted_player, audio=False)
            for flag in (Flag.INITIALIZE, Flag.PROCESSING, Flag.GAME_END):
                message = PlayerGameState(state_flag=flag.value)
                if flag == Flag.PROCESSING:
                    message.audio_data.SetInParent()
                if flag == Flag.GAME_END:
                    message.round_result.current_round = 3
                    message.round_result.remaining_hps.extend([300, 0])
                    message.round_result.elapsed_frame = 100
                engine.sendall(b"\1")
                send(engine, message.SerializeToString())
                self.assertEqual(receive(player, 1), b"\1")
                public = PlayerGameState.FromString(packet(player))
                self.assertEqual(public.state_flag, flag.value)
                self.assertFalse(public.HasField("audio_data"))
                if flag == Flag.PROCESSING:
                    key = GrpcKey()
                    key.A = True
                    send(player, key.SerializeToString())
                    self.assertEqual(GrpcKey.FromString(packet(engine)), key)
            engine.sendall(b"\0")
            self.assertEqual(receive(player, 1), b"\0")
            self.assertEqual(future.result(), {"callbacks": 1, "controller_disconnected": False,
                                               "round_results": [[3, 300, 0, 100]]})


if __name__ == "__main__":
    unittest.main()
