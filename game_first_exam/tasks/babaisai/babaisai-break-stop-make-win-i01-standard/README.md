# babaisai-break-stop-make-win-i01-standard

| | |
|---|---|
| Benchmark | Baba Is AI |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: Baba Is AI has no privileged mode, PROTOCOL §2) |
| Simulator / robot | `babaisai` / `game-agent` |
| Family / instance | `break-stop-make-win` / seed 2117382936 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
Break the blocking rule, construct a winning rule, then reach the native goal. One frozen episode, 100 actions, no reset. Native RGB rendering, without derived symbolic descriptions.

## Difficulty
Composed rule manipulation across two rooms.

## Reference solution
The offline reference uses 25 native actions. It proves reachability, not model ability or optimality; it is not included in the agent image.

## Verification
An isolated verifier validates trusted simulator evidence, native win/loss, step-dependent reward, and initial-state binding. It does not replay the trajectory.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 1 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed.
