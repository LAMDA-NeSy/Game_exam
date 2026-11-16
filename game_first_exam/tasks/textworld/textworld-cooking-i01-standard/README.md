# textworld-cooking-i01-standard

| | |
|---|---|
| Benchmark | TextWorld |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: TextWorld has no privileged mode, PROTOCOL §2) |
| Simulator / robot | `textworld` / `game-agent` |
| Family / instance | `cooking` / seed 2117382936 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
| --- | --- |

One frozen native episode; no added action-count cap, no reset. Read the in-game objective and complete it. Maximize the native score divided by the game maximum; actual victory is reported separately. Observations contain player-visible feedback, room description, inventory and objective. Use single native parser commands within the interpreter-control boundary in `spec()`, including `prepare meal` in cooking. A command may fail in the game and still consume an action. `look` and `inventory` also consume actions; `observe()` rereads cached text without consuming one. Undo, restart, save/restore and interpreter/debug commands are unavailable.

## Difficulty
Fixed seed chosen before model evaluation, without outcome-based selection. This is a small integration suite, not the complete upstream benchmark protocol.

## Reference solution
The offline reference uses 12 actions. The official generator walkthrough establishes native victory. Reference actions are isolated in `/solution`, never in the agent image.

## Verification
The separate verifier grades immutable trusted live evidence bound to the complete frozen instance hash. Native metrics are checked separately from the shared budget/termination rules. Live video and event logs are audit artifacts, not score inputs.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 1 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed.

## Details
| | |
|---|---|
| Key | Value |

### Notes
The common game service and benchmark adapter are copied from locally built digest-pinned files-only images. Text-only games use a labelled transcript video. Public-network integration track.
