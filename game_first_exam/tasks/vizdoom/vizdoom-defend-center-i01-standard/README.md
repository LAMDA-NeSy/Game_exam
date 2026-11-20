# vizdoom-defend-center-i01-standard

| | |
|---|---|
| Benchmark | ViZDoom |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: ViZDoom has no privileged mode, PROTOCOL §2) |
| Simulator / robot | `vizdoom` / `game-agent` |
| Family / instance | `defend-center` / seed 2117382936 |
| Oracle | `partial` — Exercises the frozen scenario and measures its native score along a reference trajectory. See solution/actions.json. |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
Defeat as many approaching monsters as possible from the center of the arena. The task uses the ViZDoom 1.3.2 scene and bundled Freedoom 2 assets.

## Difficulty
Turn to cover approaching enemies and manage limited ammunition.

## Reference solution
The recorded reference exercises the native scoring path and provides a reproducible example score.

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
