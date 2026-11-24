# SlimeVolley practice and scored match

Run from the repository root with the project's Harbor environment and Docker Engine 29. If the SlimeVolley files image is unavailable in your registry or local cache, run `python scripts/files_image.py build slimevolley-files` first. Choose an output directory outside the checkout. A Docker daemon running on another host needs access to that directory through the same filesystem path.

```sh
# Verify both scenarios and the saved practice controller at a shortened cutoff.
python scripts/run_slimevolley_exam.py --smoke --output /path/to/new-smoke-output

# Run one coding agent with the full 600-second practice budget.
python scripts/run_slimevolley_exam.py \
  --agent-config configs/harbor/claude-deepseek.json \
  --allow-agent-host api.deepseek.com \
  --output /path/to/new-exam-output
```

The agent config supplies exactly one agent. The runner sets the task, resource limits, timeout, and one attempt. Practice ends when the agent finishes or its 600 seconds expire. A fresh container launches the saved `gen.py` for up to 120 seconds with the public pixel client. If that file is missing, the evaluator selects `practice_gen.py` from the same collected output directory. The evaluator freezes the selected file under `official/gen.py`. A deterministic `idle` action completes the remaining frames if there is no usable selected file or the controller stops early.

Practice slots `A` and `B` are fixed. The runner samples a separate hidden seed before practice and excludes both practice seeds. For experiments comparing multiple agents on the same held-out scenario, pass `--official-seed-file` with a private file containing one integer. Every run needs a new output directory. Keep the seed file and run logs inaccessible to the practice agents.

Read `exam.json` for the independently verified official score, controller outcome, the original filename in `submission_source`, and controller/idle frame counts. The snapshot and scoring evidence are under `official/`, including `official/evidence/replay.mp4`. The Harbor job under `practice-job/` tracks the rehearsal and submission only. A simulator or evaluation infrastructure failure invalidates the run. The frozen single-match standard task is available separately through the regular SlimeVolley suite.
