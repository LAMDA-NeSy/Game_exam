# vgc-vs-random-i01-standard

| | |
|---|---|
| Benchmark | VGC |
| Mode | standard (`game-standard/2.2`) |
| Twin | — (none: single frozen battle, no privileged replay twin yet) |
| Simulator / robot | `vgc` / `game-agent` |
| Family / instance | `vs-random` / seed 0 |
| Oracle | `full` |
| Agent time budget | 600 s; tokens: protocol default (docs/protocol/running.md "Official runs") |
| Base image | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` |

## Task
Win a frozen VGC doubles battle (regulation MA, `gen9championsvgc2026regma`) against the native random opponent. Both teams are frozen in the instance; the opponent policy is `random`.

## Difficulty
Piloting a doubles team under partial information and stochastic battle mechanics (damage rolls, speed ties), with the opponent policy fixed but its in-battle RNG unseeded.

## Reference solution
See `solution/`.

## Verification
The isolated verifier checks the trusted `final.json` (win/loss, native return, action count, instance binding). It does not replay the trajectory or run the engine.

## Resources
Caps per container (PROTOCOL §6).

| Container | CPUs | Memory | Processes | GPU memory | Disk |
|---|---|---|---|---|---|
| `main` (the agent's) | 1 | 1 GiB | 256 | no GPU | 2 GiB |
| `sim` | 1 | 2 GiB | 128 | no GPU | — |
| verifier (as `main`) | 1 | 1 GiB | no cap | no GPU | 2 GiB |

- GPU: not needed.

## Details

### Compatibility and deviations
- Only the native battle environment (poke-env fork + Pokemon Showdown) is reused. VGC-Bench's RL/BC training, LLM agent, and evaluation tools are not migrated.
- The two-player battle is reduced to a single-agent episode by fixing the opponent at construction.
- The Showdown engine PRNG is not seeded from Python; single-battle outcomes are therefore not bit-reproducible. `win` is the primary metric; the framework's `mean_primary_score` (win rate over frozen instances) aggregates a family rather than claiming a single-seed binary score.
- Isolation: the Showdown server and the adapter run inside the `sim` container; the agent reaches the game only through the `server.py` HTTP protocol. Showdown must bind loopback only.

### Remaining before freeze
- Build/push the `vgc-files` image (digest `dc627df4…` is computed; `scripts/files_image.py build` needs a running Docker daemon).
- Verify the adapter's fork-specific touchpoints (see the `VERIFY` note in `adapter.py`): fixed-team construction, `SingleAgentWrapper` interface, joint-action encoding, won/lost access.
- Strengthen `fingerprint()` to hash the parsed initial battle state (not just the frozen config) once poke-env is installed.
- Fill `solution/` with a real winning reference trajectory (oracle).
