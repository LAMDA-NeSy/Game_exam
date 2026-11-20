# Tetris Gymnasium native integration

This change adds the native Tetris Gymnasium adapter, trusted schema, metric validation, files-only image and native/contract tests. Frozen Harbor tasks and a game suite are intentionally deferred.

## Reference and compatibility

The repository baseline is LAMDA-NeSy/Game_exam commit `7998e10f62811de00a0145ab90480a254a3fc827`. The integration uses the MIT-licensed [Max-We/Tetris-Gymnasium](https://github.com/Max-We/Tetris-Gymnasium) project and does not use an NES/Atari emulator or a ROM.

Version 0.2.1 is pinned because the single-reset profile used here has the same `step` dynamics, actions and rewards as 0.3.1 without making the unrelated JAX functional API a simulator dependency. Version 0.3.1 also changes repeated-reset handling and RGB observation-space metadata; this adapter does not claim those paths are identical. `SOURCE.json` records the upstream tag commit and official PyPI wheel digest.

| Area | Implementation |
|---|---|
| Execution | Harbor native agent, existing GameClient, shared runtime/server.py |
| Native backend | `gym.make("tetris_gymnasium/Tetris")`, one reset and one native step per accepted request |
| Board profile | Native 10×20 board, gravity enabled, four-piece queue, one-piece holder |
| Observation | Upstream `RgbObservation`: padded board, active piece, queue and holder; PNG transport |
| Actions | All eight native actions exposed as descriptive enum strings |
| Seeding | Native `reset(seed=...)`; seed 0 is rejected because upstream 0.2.1 treats it as unseeded |
| Reward | Native placement survival reward plus native quadratic line-clear score |
| Metrics | Total cleared lines, native return, rewarded placements and line-clear score |
| Completion | Native game-over terminates; future tasks must provide a public action cap |

## Isolation and audit

Only `image_png_base64` is returned in adapter observations. The image is produced by the upstream RGB wrapper and contains information normally visible in Tetris: the board, active piece, next-piece queue and held piece. Exact arrays, active coordinates, random bag contents and RNG state stay inside the simulator and are used only by `fingerprint()` for audit integrity.

The adapter is designed for the existing standard-mode main/sim/verifier boundary. A future frozen task must keep its instance in sim/verifier, expose only the public client to main, and use a separate no-network verifier. No frozen Tetris task, target instance, solution or reference trajectory is included in this change.

## Native semantics

Tetris Gymnasium has no native time-limit truncation. The episode terminates when a new tetromino cannot spawn. A future frozen instance must set the shared public `max_steps` cap; reaching that cap remains a budget end rather than a native termination.

The primary metric profile is total native lines cleared. `target_lines` supplies a binary compatibility success label without changing native dynamics or ending the episode early. The adapter preserves each native reward increment and checks the pinned placement reward formula before recording it.

## Validation commands

```bash
python game_first_exam/tests/test_tetris_contract.py
python game_first_exam/tests/test_tetris_native.py
```

The native test requires the pinned Tetris Gymnasium environment and compares direct native calls with the adapter across seeds, all actions, observations, rewards, termination and read-only methods. Contract tests use a deterministic engine double to exercise the shared service and grader without publishing a task.

## Sources

- https://github.com/Max-We/Tetris-Gymnasium/tree/0.2.1
- https://max-we.github.io/Tetris-Gymnasium/environments/tetris/
- https://max-we.github.io/Tetris-Gymnasium/utilities/wrappers/
- https://pypi.org/project/tetris-gymnasium/0.2.1/
