# firewater-forest-exit-i01-standard

| | |
|---|---|
| Benchmark | GameWorld Forest Temple |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: GameWorld Forest Temple has no privileged mode, PROTOCOL §2) |
| Simulator / robot | `firewater` / `game-agent` |
| Family / instance | `forest-exit` / seed 0 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
Bring Fireboy and Watergirl to their matching doors in the original Forest Temple level one.

## Difficulty
Cross three pools and climb the temple. The two players take turns standing on pressure plates to move the purple lift. Push the crate to reach the final ledge.

## Reference solution
The oracle plays a recorded sequence of paired keyboard movements through the public game client. Actions are grouped by room feature in solution/route.json.

## Verification
The isolated verifier checks the native terminal event and level number. Death and an unfinished episode earn zero even if every diamond was collected.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 1 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed.
