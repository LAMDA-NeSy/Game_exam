# fightingice-zen-kick-p1-i01-standard

| | |
|---|---|
| Benchmark | FightingICE |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: native match is isolated; no privileged replay task is implemented) |
| Simulator / robot | `fightingice` / `game-agent` |
| Family / instance | `zen-kick` / seed 0 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
Control P1 ZEN against the frozen KickAI in one native three-round match. The
profile is delayed structured FrameData. No reset, no wall-clock realtime.
Versioned conditions and differences are in the benchmark README.

## Difficulty
Minimal native combat and program-control smoke coverage, not tournament difficulty.

## Reference solution
The offline controller wins the three native rounds by remaining outside the
opponent's short attack range. It is confined to solution/, not the agent image.

## Verification
The separate verifier checks trusted native rounds, fixed-denominator score,
ending flags and action counts. Internal frame hashes and the audit transcript
are not public observations. The transcript is not a native gameplay recording.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 1 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed.
