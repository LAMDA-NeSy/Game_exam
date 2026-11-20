# vmage-supermario-l01-i01-standard

| | |
|---|---|
| Benchmark | V-MAGE |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: this V-MAGE task exposes only the isolated standard client) |
| Simulator / robot | `vmage` / `game-agent` |
| Family / instance | `l01` / seed 0 |
| Oracle | `partial` — Frozen actions verify a positive native score only; no full-score or optimal-policy claim. |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.10.12-slim-bookworm@sha256:4d440b214e447deddc0a94de23a3d97d28dfafdf125a8b4bb8073381510c9ee2` |

## Task
Move and jump to collect coins and defeat enemies while avoiding death. Your score is the native on-screen point counter, including native item and enemy rewards. Death or the native frame limit ends the episode; accumulated points are retained. The native screenshot counter limit is 400, including initialization. It is not a count of client requests. Frozen V-MAGE commit 95d5d4a445bb0b75cce765c93107d87f84613e4d, code level1, seed0. No reset. Internal score group: vmage_supermario.

## Difficulty
Initial native level; smoke integration only.

## Reference solution
The frozen 11-decision reference verifies a positive native score only; it is a partial reference with the actual 3/5-frame action sampling. It is excluded from the model-facing image and is not a model score or optimality proof.

## Verification
An isolated verifier validates the trusted live final, instance binding, native score decomposition, counter/terminal consistency, and score differences. It does not replay the native game. Non-Race success is only a positive-score compatibility flag. Audit video samples decision frames and is not a complete native 30 FPS replay.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 1 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed.

## Details

### Notes
See [V-MAGE notes](../README.md) for source provenance, native loop/observation adaptations and reproduction boundaries. Original native code and assets are fetched from the hash-pinned archive into the simulator; they are not copied into the agent or stored as vendored sources in this repository. Distribution permission remains unconfirmed; internal research only.
