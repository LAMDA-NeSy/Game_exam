# crafter-survival-i03-standard

| | |
|---|---|
| Benchmark | Crafter |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: Crafter has no privileged mode, PROTOCOL §2) |
| Simulator / robot | `crafter` / `game-agent` |
| Family / instance | `survival` / seed 470363396 |
| Oracle | `partial` — Frozen reference actions demonstrate the wooden-pickaxe auxiliary milestone; not a full 22-achievement policy (solution/actions.json and README Reference solution). |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
| --- | --- |

One frozen native episode; 10000 native actions, no reset. Explore, survive, and unlock as many of the 22 native achievements as possible. Your primary metric is achievement coverage; the suite also reports the geometric Crafter achievement score. Crafting a wooden pickaxe is an auxiliary binary milestone only, not the full objective. Death ends the episode but does not erase achievements.

## Difficulty
Fixed seed chosen before model evaluation, without outcome-based selection. This is a small integration suite, not the complete upstream benchmark protocol.

## Reference solution
The reference uses 20 native actions to establish the auxiliary wooden-pickaxe milestone, then exits. It does not wait for death and is not a full achievement policy. The engine is unmodified; native set iteration does not guarantee identical trajectories across processes.

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
