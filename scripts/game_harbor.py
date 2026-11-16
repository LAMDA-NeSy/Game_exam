"""Harbor's native job plugin: supplemental game provenance and derived scores only."""

import json
from pathlib import Path

from game_preflight import validate_task
from game_reports import write_harbor_report
from game_runtime import RuntimeCapture, report_code_metadata, runner_metadata, validate_report_code
from game_schemas import register_schemas


class GameRecords:
    async def on_job_start(self, job):
        # This reducer's scope is one graded attempt per task and execution mode. Others can
        # still use plain Harbor, without this single-attempt summary plugin.
        if (
            job.config.n_attempts != 1
            or len(job.config.agents) != 1
            or job.config.retry.max_retries != 0
            or job.config.is_regrade
            or job.config.install_only
            or job.config.verifier.disable
        ):
            raise ValueError("game reports require one agent, one attempt, verification and no automatic retries")
        register_schemas()
        tasks = list(job.config.tasks)
        for dataset in job.config.datasets:
            tasks.extend(await dataset.get_task_configs())
        seen = set()
        modes = set()
        metrics = {}
        for entry in tasks:
            if entry.path is None or entry.git_url or entry.name:
                raise ValueError("game reports require local frozen task directories")
            task = Path(entry.path).resolve()
            if task.name in seen:
                raise ValueError("duplicate game task")
            seen.add(task.name)
            from task_conventions import mode_of
            modes.add(mode_of(task))
            if len(modes) > 1:
                raise ValueError("game reports require one execution mode; select --standard, --privileged or --realtime")
            instance = json.loads((task / "tests/instance.json").read_text())
            previous = metrics.setdefault(instance["benchmark"], instance["metric_spec"])
            if previous != instance["metric_spec"]:
                raise ValueError("incompatible metric definitions within benchmark")
            validate_task(
                {"name": task.name, "benchmark": instance["benchmark"], "family": instance["family"]}, task_path=task
            )
        if not seen:
            raise ValueError("no game tasks")
        self.job = Path(job.job_dir)
        self.path = self.job / "game-provenance.json"
        if self.path.exists():
            self.provenance = json.loads(self.path.read_text())
            validate_report_code(self.provenance)
            # Resuming a partially captured job would need merging image evidence.
            raise ValueError("use a new job for game reports; existing provenance is preserved")
        runtime = runner_metadata()
        # Harbor records its own version, agent/model, retry policy and task hashes.
        for duplicate in ("harbor_version", "interaction_policy"):
            runtime.pop(duplicate, None)
        self.provenance = {
            "schema": "game-provenance/1.0",
            "runtime": runtime,
            "report_code_sha256": report_code_metadata(),
            "status": "running",
        }
        self.save()
        self.capture = RuntimeCapture(self.job)
        self.capture.start()

    def save(self):
        self.path.write_text(json.dumps(self.provenance, indent=2) + "\n")

    async def on_job_end(self, job_result):
        try:
            self.provenance["runtime_images"] = self.capture.finish()
            summary = write_harbor_report(self.job)
            self.provenance["status"] = "complete" if summary["complete"] else "incomplete"
        except Exception as exc:
            # Harbor logs plugin failures but retains its original result. Make
            # report failures explicit on disk too; never manufacture a grade.
            self.provenance["status"] = "report_error"
            self.provenance["error_type"] = type(exc).__name__
            raise
        finally:
            self.save()
