# vizdoom-basic-i01-standard

| | |
|---|---|
| Benchmark | ViZDoom |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: ViZDoom has no privileged mode, PROTOCOL §2) |
| Simulator / robot | `vizdoom` / `game-agent` |
| Family / instance | `basic` / seed 2117382936 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
Find and defeat the single target in the room. This is the unmodified ViZDoom 1.3.2 Basic scenario, using the bundled Freedoom 2 assets and a frozen seed.

## Difficulty
First-person target localization and lateral movement.

## Reference solution
The oracle exercises the public client with 4 frozen decisions from this initial state.

## Verification
The isolated verifier validates the native objective, game return, tic count and instance binding of the live episode.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 1 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed.
