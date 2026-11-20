# vizdoom-deadly-corridor-i01-standard

| | |
|---|---|
| Benchmark | ViZDoom |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: ViZDoom has no privileged mode, PROTOCOL §2) |
| Simulator / robot | `vizdoom` / `game-agent` |
| Family / instance | `deadly-corridor` / seed 2117382936 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
Cross the corridor and pick up the green armor vest while surviving enemy fire. The task uses the ViZDoom 1.3.2 scene and bundled Freedoom 2 assets.

## Difficulty
Combat, navigation and survival under pressure.

## Reference solution
Recorded reference actions complete the scenario's objective.

## Verification
The independent verifier checks the frozen instance, native return, tic ledger and ending evidence.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 1 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed.
