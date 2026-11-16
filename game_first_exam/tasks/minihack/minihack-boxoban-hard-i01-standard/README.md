# minihack-boxoban-hard-i01-standard

| | |
|---|---|
| Benchmark | MiniHack |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: MiniHack has no privileged mode, PROTOCOL §2) |
| Simulator / robot | `minihack` / `game-agent` |
| Family / instance | `boxoban-hard` / seed 2117382936 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
Push all four boulders onto the four fountains. A boulder moves one square when you walk into it and the square behind it is clear.

## Difficulty
Native MiniHack Boxoban-Hard.

## Reference solution
A recorded sequence of 66 native actions reaches the original success condition on the frozen instance.

## Verification
The separate verifier grades the simulator's recorded episode.

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
Native environment `MiniHack-Boxoban-Hard-v0` with a 400-action limit. The instance files pin the seed, initial state, and observation profile.
