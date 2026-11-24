# vex3-act-one-i01-standard

| | |
|---|---|
| Benchmark | GameWorld Vex 3 |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: GameWorld Vex 3 has no privileged mode, PROTOCOL §2) |
| Simulator / robot | `vex3` / `game-agent` |
| Family / instance | `act-one` / seed 42 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
Clear the first numbered act in one life using keyboard input.

## Difficulty
Time jumps over rotating saws, slide underneath a spiked overhang, and climb to the exit using the level's walls and ziplines. The first death ends the attempt.

## Reference solution
See `solution/`.

## Verification
The simulator reads GameWorld's native completion event and death count. The isolated verifier validates the terminal state and awards one point for a deathless clear of Act 1.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 1 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed.
