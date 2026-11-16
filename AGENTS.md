# Working on Game Exam

Read README.md, docs/game_framework.md and the selected benchmark's README before editing.

- This repository contains games only. Do not add robot benchmarks, website source, local job logs, credentials, or generated Docker contexts.
- Keep native benchmark dynamics, rewards and termination in `game_first_exam/benchmarks/<game>/adapter.py`; record deviations in that benchmark's README. Coding agents execute through native Harbor agents, with no custom model gateway.
- Common interaction, budget checks, collection, and grading live in `game_first_exam/runtime/`. Shared connection readiness lives in `shared/connection/`; shared monitoring in `images/monitor/`.
- Use `scripts/task_conventions.py` task discovery. Tasks live in `game_first_exam/tasks/<game>/<task>/`, and are self-contained at runtime. Do not import host repository files from running task containers.
- Register native configuration validation in `configs/game_benchmarks.toml`; declare frozen suites in `configs/game_suites/`. Unknown configuration and reducers must fail before execution.
- Read `docs/templates/game-standard/README.md` before editing instructions. State the task, observations, actions, client calls, scoring and limits accurately. Keep audit and packaging notes in benchmark README files.
- Normalize changed tasks with `python scripts/task_conventions.py <task-dir>`, which refreshes DIGEST. Set resource rules in `scripts/task_resources.toml` rather than editing generated resource paragraphs.
- Files-only images pin content and executable modes. Source changes require updated versions and digests; moving a byte-identical source directory does not change the OCI payload. Check all suites after any shared change.
- Run `python ci_checks/check-games.py`, common tests and native adapter tests. Launcher/report/configuration changes also require `game_first_exam/tests/test_game_harbor.py` under Harbor 0.23.0.
- Harbor owns config.json, lock.json, result.json and agent logs. GameRecords adds derived game reports and image provenance; never overwrite the native records. Do not combine incompatible observation modes in one reported score.
- Never commit API keys or personal configuration. Keep `jobs/`, `output/` and website files outside the public repository. Model calls, image publication and deployments are separate from local regression tests.
