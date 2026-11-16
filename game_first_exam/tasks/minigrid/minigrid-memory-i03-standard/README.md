# minigrid-memory-i03-standard

| | |
|---|---|
| Benchmark | MiniGrid |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: the game suite evaluates partial observation only) |
| Simulator / robot | `minigrid` / `grid-agent` |
| Family / instance | `memory` / seed 470363396 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
| --- | --- |

Observe the object in the starting room, remember its type, and traverse the hallway. At the final split, approach the object matching the starting cue. Reaching the corridor cell in front of the matching object succeeds; approaching the other object ends the episode in failure. There is no green goal tile in this task. Environment: `MiniGrid-MemoryS11-v0`. One episode, 605 native actions, no reset. This is a fixed test instance in the native-settings development subset.

## Difficulty
Remembering an earlier visual cue; 7×7 local observations. The three suite seeds were drawn before model evaluation, without outcome-based selection.

## Reference solution
The verifier-owned action sequence succeeds in 8 steps. It was found offline using full simulator state, then checked against real transitions. It proves reachability only; it is not an evaluated policy and is never copied into the agent image.

## Verification
The separate verifier checks the trusted live verdict and initial-state hash. It preserves native failure rewards, rejects missing or malformed evidence, and reports binary success. No agent-written score is trusted. Video and action logs are audit artifacts, not scoring inputs.

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
| Protocol | game-standard/2.2 |
| Instance seed | 470363396 |

### Notes
Shared runtime files are pinned by digest in `game_first_exam/images/game-files/FILES.json` and `game_first_exam/images/minigrid-adapter-files/FILES.json`. Build that files-only image locally before a trial. Public-network integration track; results are not an official upstream leaderboard entry.
