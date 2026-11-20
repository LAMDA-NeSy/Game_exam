# rocketleague-first-goal-i01-standard

| | |
|---|---|
| Benchmark | GameWorld Rocket League 2D |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: GameWorld Rocket League 2D has no privileged mode, PROTOCOL §2) |
| Simulator / robot | `rocketleague` / `game-agent` |
| Family / instance | `first-goal` / seed 42 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
Score first in a single-player match against the native AI. The reference solution drives and boosts through the public client. The verifier checks both teams’ goal counts.

## Difficulty
Start at a fixed kickoff against the default single-player opponent. Releasing boost early gives the opponent time to recover and counterattack.

## Reference solution
See `solution/`.

## Verification
The verifier checks the two native goal counters. A first goal for the player earns one point. Conceding or exhausting the action budget earns zero.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 1 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed.
