# Game source tree

- `runtime/`: shared client/service, contracts, validation, grading, recording and reducers; `modes/` holds privileged and realtime execution.
- `benchmarks/`: MiniGrid, Crafter, TextWorld, Baba Is AI and MiniHack adapters, schemas, metric rules and native dependencies.
- `tasks/<game>/<task>/`: 44 frozen self-contained Harbor task directories.
- `images/`: seven game files-only image definitions, built from explicit source manifests.
- `tests/`: shared and native regressions, fixtures and pinned dependency environments.

The client reuses `shared/connection/service_connection.py` via the shared connection-files image. Resource monitoring remains under `images/monitor/`. No original robot source/task/image tree or legacy MiniGrid prototype is included.

Run through `harbor run --game-suite <suite> --standard -a <agent> -m <model>` or a native agent profile. `--list` validates without starting a run. Harbor owns execution and original records; `game_harbor:GameRecords` adds optional provenance and derived reports. The compatibility `scripts/run_games.py` delegates to the same execution path.

See the [root README](../README.md), [framework](../docs/game_framework.md), [native profiles](../configs/harbor/README.md) and [instruction template](../docs/templates/game-standard/README.md).
