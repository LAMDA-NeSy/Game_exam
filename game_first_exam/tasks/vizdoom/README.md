# ViZDoom standard integration

The `vizdoom` suite contains eleven single-player scenes from ViZDoom 1.3.2 with bundled
Freedoom 2 assets. The `vizdoom-smoke` suite runs Basic and My Way Home.

## Controls and observations

The public client accepts a positive integer `tics` argument, defaulting to one tic. ViZDoom
holds the selected buttons for that duration and stops early when the native episode or the
600-second agent budget ends. The trusted tic ledger records requested and executed durations
in step order. Defend the Line and Take Cover use native death or the public wall clock to end
their episodes. Finite scenes use their frozen native tic limits.

All tasks expose native 320×240 first-person RGB. Basic Notifications also exposes the
latest native in-game message observed by the simulator. Deathmatch accepts native binary
buttons and continuous look, turn and strafe values, applied each tic. Audio, automap, depth,
label buffers, object metadata and sector metadata stay inside the evaluation boundary.
Frozen seeds and binary assets are verified during initialization. The final image can be
absent on an engine terminal event, and a replay ends with the last available real frame.

## Scoring

The report covers every frozen task. Its objective completion rate and objective family macro
cover Basic, My Way Home, Basic Notifications, Predict Position and Deadly Corridor. A wrong
target or a missed rocket are valid failures. Defend the Center, Defend the Line, Take Cover,
Health Gathering, Health Gathering Supreme and Deathmatch report their native returns and
scenario statistics. They have a per-scenario score record without a shared return scale.
The verifier checks native game evidence against the frozen scene.

## Running

```bash
harbor run --game-suite vizdoom --standard --list
harbor run --game-suite vizdoom --standard -c configs/harbor/oracle.json --plugin game_harbor:GameRecords
```

The integration uses the pinned Linux x86-64 wheel for CPython 3.12. Upstream component
notices include Freedoom’s BSD license. See [official scenario descriptions](https://vizdoom.farama.org/environments/default/).
