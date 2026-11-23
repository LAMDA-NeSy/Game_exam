# slimevolley-pixel-vs-baseline-i01-standard

| | |
|---|---|
| Benchmark | SlimeVolleyGym |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: SlimeVolleyGym has no privileged mode, PROTOCOL §2) |
| Simulator / robot | `slimevolley` / `game-agent` |
| Family / instance | `pixel-vs-baseline` / seed 2117382936 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
Control the right player in one native pixel match against the built-in left player.

## Difficulty
Continuous motion, pixel-based ball tracking and timed jumps.

## Reference solution
A frozen offline state-policy trace earns +1 in 3000 frames. The oracle uses the same public action client as the coding agent.

## Verification
The independent verifier checks the sealed native score, lives, steps and ending against its frozen instance.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 1 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed.
