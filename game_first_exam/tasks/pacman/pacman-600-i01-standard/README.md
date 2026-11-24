# pacman-600-i01-standard

| | |
|---|---|
| Benchmark | Pac-Man |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: Pac-Man has no privileged mode, PROTOCOL §2) |
| Simulator / robot | `pacman` / `game-agent` |
| Family / instance | `score-600` / seed 42 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
Collect pellets and avoid ghosts until the native game score reaches 600.

## Difficulty
Continuously moving ghosts require route planning and timely turns in the maze.

## Reference solution
The 24-action route in `solution/` scored 1.0 in the Harbor oracle run. The ghost-collision control scored 0.0.

## Verification
The isolated verifier validates the native score and awards one point at 600, zero on game over or budget exhaustion.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 1 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed.
