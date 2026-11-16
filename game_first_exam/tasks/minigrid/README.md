# MiniGrid integration

The current development suite contains six native task families × three fixed seeds: 18 standard episodes. It uses `game-standard/2.2` and the `native-observation-v1` profile. The obsolete i00 prototype and its separate runtime are not included in this game-only repository.

| Family | Native environment |
|---|---|
| Empty-Random | `MiniGrid-Empty-Random-6x6-v0` |
| DoorKey | `MiniGrid-DoorKey-8x8-v0` |
| MultiRoom | `MiniGrid-MultiRoom-N4-S5-v1` |
| Lava Crossing | `MiniGrid-LavaCrossingS9N1-v0` |
| Memory | `MiniGrid-MemoryS11-v0` |
| Dynamic Obstacles | `MiniGrid-Dynamic-Obstacles-8x8-v0` |

MiniGrid 3.2.0's corrected MultiRoom v1 uses four rooms; v0 is not substituted. Seeds are 2117382936, 1056882141 and 470363396, selected before model evaluation and reused across families. Frozen native step limits vary by environment; the adapter verifies them at startup. There is no shared 256-action override. The agent wall-clock budget is declared per task.

Observations serialize the native mission, direction and egocentric 7×7 encoded image array. `image[x][y]` stores object/color/state; this is a symbolic observation, not an additional PNG or a full map. Native wall visibility remains in force. Full native renders are recorded for audit/video and are not silently sent to the agent. State fingerprints include hidden state/RNG and remain internal.

Actions use native meanings: left/right/forward/pickup/drop/toggle/done, narrowed to the actual environment action space. Dynamic Obstacles has only its native three actions. Each accepted action advances the native engine; original rewards and end flags are retained. Memory's target is determined by its earlier cue rather than a green goal. Success is the native positive-reward termination; invalid/stale submissions do not execute an extra action.

```bash
harbor run --game-suite minigrid --standard --list
harbor run --game-suite minigrid --standard -l 1 -c configs/harbor/oracle.json \
  --plugin game_harbor:GameRecords --job-name minigrid-oracle
```

Reference actions are frozen per instance under solution/ and are excluded from the agent's environment. Tests compare native trajectories, seed reproduction, end semantics and read-only observations in the pinned MiniGrid dependency environment. See [test environments](../../tests/envs/README.md), [suite](../../../configs/game_suites/minigrid.toml), [framework](../../../docs/game_framework.md) and each task's instruction for concrete controls.

These are small development instances, not the entire MiniGrid catalog or a held-out generalization leaderboard. Installation, runtime and shared trust-boundary details are in the [root README](../../../README.md).
