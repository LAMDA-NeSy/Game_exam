# V-MAGE standard tasks

V-MAGE freezes 34 seed-0 levels across RaceGame (9), FlappyBird (7), Pong (3), SuperMario (10), and Tempest Run (5). All five use an isolated standard client, one live episode and no reset. Each game's native raw score is reported separately. No Elo or cross-game raw-score mean is produced. Race success means reaching the trophy; other success fields are positive-score compatibility flags.

## Suites

| Harbor suite | Coverage |
| --- | --- |
| `vmage` | The 33 levels in the upstream default suite |
| `vmage-extra` | Tempest Run L5 |
| `vmage-smoke` | One L1 task for each of the five games |

Use `harbor run --game-suite vmage --standard --list` to inspect the default suite.

## Native source and packaging

Source commit: `95d5d4a445bb0b75cce765c93107d87f84613e4d`. Archive SHA256: `1047daa50004003eb9848205e1c420679e51d54d9a38acd3155da4aa8680e919`. The selected source/asset manifest and dependencies are recorded under `game_first_exam/benchmarks/vmage/common/` and in each instance. Builds fetch and verify the original selected payload; native implementation and asset bytes are not vendored into this checkout. Source and asset redistribution permission is unresolved: internal research only, with no image publication.

## Native behavior and adaptations

The effective upstream sampling is three frames per decision, except Mario's five. Tempest uses NONE in passive frames; the other games repeat the selected action. The native dt is 0.033, paced at 30 FPS. Initialization performs the original step('None', 0) before the first screenshot. The frame ledger preserves upstream capture order, including omitted passive terminal captures. The native limits for Race and SuperMario count capture-ledger entries. Each frozen instance specifies its limit. Native collision and reward logic remains in the original games. Invalid client actions do not advance or capture frames and do not trigger the original runner's random fallback.

## Visible input and audit frames

The public input is a native screenshot scaled with pygame.transform.scale to height 360: FlappyBird 202x360, other games 480x360. The authored instruction describes the controls and scoring. Parsed objects, coordinates, hidden parameters and native info are not supplied. The coding agent manages its own image history rather than receiving the original naive agent's fixed history window. Reads use cached images because extra native rendering could change Race collision handling or Tempest obstacle generation. The audit video samples native-resolution decision frames; it is not a complete 30 FPS replay.

## Scores and limits

Raw scores are Race 100/0; FlappyBird 0.5 per pipe half, or 1 per pair; Pong total paddle returns; Mario dashboard.points; and Tempest int(z/10)*10. Native caps, death and rewards remain. The frozen agent deadline is 600 seconds per task. Model thinking and tool execution consume wall time while physics waits. Calendar time is not virtualized. Tempest explosion visuals use wall time, so full pixel identity across different delays is not claimed. Fingerprints exclude cosmetic timestamps and provide audit binding rather than restorable checkpoints. Native dependencies, SDL and fonts are frozen for the tested setup.

## Reference and verification

The five L1 smoke references check the trophy condition in Race and positive scores in the other four games. Other reference traces exercise the native action and scoring path and may finish with zero points. They are not exposed to the evaluated model. An independent verifier grades trusted live evidence, without trusting agent-written scores or claiming native trajectory replay. Model evaluation and publication are separate actions.
