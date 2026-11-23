# Gymnasium 2048 native integration

This directory adds a thin adapter, trusted schema, metric validation and source provenance for the MIT-licensed
[`gymnasium-2048`](https://github.com/Quentin18/gymnasium-2048) environment. Frozen Harbor tasks, a game suite and
benchmark registration are intentionally deferred.

## Frozen native profile

| Area | Implementation |
|---|---|
| Upstream | `gymnasium-2048==0.1.2`, tag `v0.1.2`, commit recorded in `SOURCE.json` |
| Environment | `gymnasium_2048/TwentyFortyEight-v0`, native 4x4 board and 16 one-hot exponent channels |
| Observation | Native 400x460 RGB rendering of the board and cumulative score, transported as PNG |
| Actions | All four native actions: up, right, down and left |
| Randomness | Native `reset(seed=...)`; legal moves spawn a 2 tile with probability 0.9 or a 4 tile with probability 0.1 |
| Reward | Native merge score increment; cumulative native reward is the standard 2048 score |
| End | Native termination only when no legal move remains; future tasks must also set a public action cap |
| Metrics | Native score, maximum tile, valid/invalid moves and a non-terminating 2048-tile success label |

## Isolation

Only `image_png_base64` is returned to the agent. The upstream one-hot observation and `info` object are deliberately
not forwarded because `info["board"]` contains the exact internal board. The board exponent array, RNG state, native
score, move legality and counters remain in the simulator and contribute to `fingerprint()` for audit integrity.
Rendering is cached after reset and every accepted action, so `observe()`, `spec()`, `metrics()` and `frame()` are
read-only and cannot advance RNG.

No task, solution, reference trajectory or container stack is included. A later task PR must separately verify the
main/simulator/verifier mounts, agent network policy and a no-network verifier before the benchmark is registered.

## Validation

`test_game2048_contract.py` exercises the shared service, schema, metric validator and public isolation with a
deterministic native-shaped engine double. `test_game2048_native.py` compares the adapter to direct calls into the
pinned upstream environment across seeds, every action, trajectories, rewards, RGB frames and internal state.
