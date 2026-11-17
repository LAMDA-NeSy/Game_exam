# vgc-vs-random-i01-standard

| | |
|---|---|
| Benchmark | VGC |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: single frozen battle, no privileged replay twin yet) |
| Simulator / robot | `vgc` / `game-agent` |
| Family / instance | `vs-random` / seed 0 |
| Oracle | `full` |
| Agent time budget | 600 s |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
Win a frozen VGC doubles battle (regulation MA, `gen9championsvgc2026regma`) against the native random opponent. Both teams are frozen in the instance; the opponent policy is `random`.

## Compatibility and deviations
- Only the native battle environment (poke-env fork + Pokemon Showdown) is reused. VGC-Bench's RL/BC training, LLM agent, and evaluation tools are not migrated.
- The two-player battle is reduced to a single-agent episode by fixing the opponent at construction.
- The Showdown engine PRNG is not seeded from Python; single-battle outcomes are therefore not bit-reproducible. `win` is the primary metric; the framework's `mean_primary_score` (win rate over frozen instances) aggregates a family rather than claiming a single-seed binary score.
- Isolation: the Showdown server and the adapter run inside the `sim` container; the agent reaches the game only through the `server.py` HTTP protocol. Showdown must bind loopback only.

## Verification
The isolated verifier checks the trusted `final.json` (win/loss, native return, action count, instance binding). It does not replay the trajectory or run the engine.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 2 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed (random opponent, CPU only).

## TODO before freezing
- Replace `team1`/`team2` with real frozen Showdown team text (from `vgc-bench/teams/reg_ma/`).
- Pin `poke-env` fork commit/version in `requirements.txt`, `instance_schema.py` and `instance.json`.
- Finalize the adapter's `observe()` serialization and the action grammar; then fill the `### Observations` section of `instruction.md`.
- Compute `initial_state_sha256` by constructing the adapter once and hashing `fingerprint()`.
- Build/pin the `vgc-files` image and regenerate `DIGEST` (`scripts/task_conventions.py`).
