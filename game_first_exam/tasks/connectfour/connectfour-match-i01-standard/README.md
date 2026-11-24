# connectfour-match-i01-standard

| | |
|---|---|
| Benchmark | Connect Four |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: Connect Four has no privileged mode, PROTOCOL §2) |
| Simulator / robot | `connectfour` / `game-agent` |
| Family / instance | `fixed-opponent` / seed 42 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
Play Red from an empty native 7×6 PettingZoo board. Each move is one column; the fixed Yellow opponent replies if the match is still live. Win before the 21-decision budget runs out.

## Difficulty
The opponent takes an immediate winning move and blocks a one-move threat; otherwise it picks a deterministic legal column. This is one frozen introductory match, not a calibrated difficulty scale.

## Reference solution
The 12-decision reference wins in 23 total plies. A separate 12-decision control loses in 24 plies. Neither policy needs internal simulator access.

## Verification
The isolated verifier reconstructs every placement from the trusted native move log and checks both the opponent policy and native outcome. A Red win is success (1); a draw, loss, illegal move, or exhausted decision budget is 0.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 1 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed.
