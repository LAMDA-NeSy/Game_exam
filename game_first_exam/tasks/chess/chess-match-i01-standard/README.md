# chess-match-i01-standard

| | |
|---|---|
| Benchmark | Chess |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: Chess has no privileged mode, PROTOCOL §2) |
| Simulator / robot | `chess` / `game-agent` |
| Family / instance | `standard-start` / seed 2117382936 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
White plays from the standard starting position against the frozen hash-based opponent. The public decision limit is 128 and the coding agent's time budget is 600 seconds. See the [benchmark audit](../README.md) for source, observation and grading details.

## Difficulty
Engineering smoke match against a deterministic legal-move policy. Difficulty remains uncalibrated.

## Reference solution
The frozen client route reaches a native White checkmate in 26 decisions and 51 board plies. The `solution/` directory is reserved for reference runs.

## Verification
The isolated verifier checks the final result, decision counts, trace digest and black replies against the frozen policy.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 1 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed.
