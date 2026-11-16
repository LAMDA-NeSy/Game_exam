# minihack-room-i01-standard

| | |
|---|---|
| Benchmark | MiniHack |
| Mode | standard (`game-standard/2.2`) |
| Twin | `minihack-room-i01-privileged` |
| Simulator / robot | `minihack` / `game-agent` |
| Family / instance | `room` / seed 2117382936 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
Reach the down staircase in the native 5x5 room. Native defaults, seed 2117382936, 100 native actions maximum, no reset. Source and dependencies are pinned in the instance and MiniHack files image.

## Difficulty
Basic navigation.

## Reference solution
The offline reference uses 4 native actions and earns native return 1. It verifies reachability, not optimality or model ability; it is excluded from the agent image.

## Verification
The isolated verifier checks trusted simulator outcomes, native return, end status, action count and instance binding. It does not replay the trajectory. The fingerprint covers available native observations, seeds and counters, not a complete NetHack checkpoint. The audit video is a terminal transcript, not an added agent observation.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 1 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed.
