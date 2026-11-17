# VGC native smoke integration

The `vgc` suite contains a frozen Pokémon VGC doubles battle (regulation MA,
`gen9championsvgc2026regma`) against the native random opponent. The native battle
engine is poke-env (the `vgc-bench` fork, unmodified) driving a pinned Pokemon
Showdown simulator. Only the environment is reused; VGC-Bench's RL/BC training,
LLM agent and evaluation tools are not migrated.

## Native settings and mode differences

- The two-player battle is reduced to a single-agent standard episode by fixing the
  opponent at construction (`opponent_policy`).
- The joint doubles action (two Pokémon) is expressed as one text action per turn.
- The Showdown engine PRNG is not seeded from Python, so a single battle is not
  bit-reproducible. `win` is the primary metric; the framework's `mean_primary_score`
  (win rate) aggregates frozen instances.
- Isolation: Showdown and the adapter run inside the `sim` container; the agent
  reaches the game only through the `server.py` HTTP protocol.

## Coding-agent interface audit

| Boundary | Native behavior / public evaluation behavior |
|---|---|
| Environment | poke-env DoublesEnv + pinned Showdown; no engine modification |
| Initialization | Frozen teams, seed, regulation, opponent policy are evaluation conditions |
| Observation | Native battle state serialized as JSON; see the adapter and instruction |
| Action | One text action per turn (the joint doubles order) |
| Feedback | observe/step return observation, step, done, steps_remaining, time_left_s |
| Score | `win` (0/1) per episode; `mean_primary_score` (win rate) aggregates a family |
| Ending | Native win/loss; timeout/agent exit seals the episode without fabricating a win |

## Task instructions

The instruction follows the game-standard authoring guide. Compatibility and audit
notes live in this README rather than in the agent prompt.
