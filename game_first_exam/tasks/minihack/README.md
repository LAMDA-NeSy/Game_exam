# MiniHack native smoke integration

The `minihack` smoke suite contains MiniHack-Room-5x5-v0 and MiniHack-River-v0, each at seed 2117382936. The independent `minihack-balrog` smoke suite contains the eight MiniHack environment IDs selected by [BALROG](https://github.com/balrog-ai/BALROG/blob/main/balrog/config/config.yaml#L86-L94). Both suites use the Game First Exam coding-agent interface and completion score. Each environment contributes one frozen instance.

Room and River instantiate their native environments with `gym.make(env_id)`. The default eight compass directions, native rewards, stalled-step penalty and episode limits (100 / 350) are preserved. Native terminated/truncated flags pass through to internal records and grading. The harness sets a 600-second agent timeout and container caps.

MiniHack 1.0.2 source commit 95b11cc8db68d72a7fe6e7540e75b568b7a811d8 is installed from a hashed archive, unmodified, with NLE 1.1.0 and Gymnasium 1.0.0. NLE core and display seeds both use the frozen instance seed, reseed=False; Gymnasium reset receives the same seed. NetHack also reads the real calendar (moon phase and Friday the 13th). Since suite 0.1.1, the simulator's calendar starts at 2026-11-13 12:00:00 UTC, using hash-pinned upstream libfaketime 0.9.12. This preserves the original frozen initial states, including Friday-the-13th behavior, without patching the engine. Only simulator calendar time is virtualized; monotonic deadlines, the agent, verifier and host retain real time. The complete clock profile is in each frozen instance. Cross-platform identity is not claimed beyond tested platforms.

Room exposes the `player-crop-9x9-v1` observation profile from suite 0.1.28. The public client returns `glyphs_crop`, `chars_crop`, `colors_crop`, `specials_crop`, `blstats` and `message` as JSON lists. River uses `native-observation-v1`, which also includes the four 21×79 display arrays. The native display supplies the audit replay and the full engine observations enter the state fingerprint along with exposed seeds and counters. The primary metric `completion_score` is 100 for native success and 0 for a valid unsuccessful episode. The existing family_macro reducer summarizes these two task families. The native cumulative reward is available in audit records.

Run `harbor run --game-suite minihack --standard -a oracle` for Room and River, or use `--suite minihack-balrog` for the eight-task selection. Use `--agent nop` to verify grading for a session with no actions. Reference actions are frozen in `solution/` and stay on the verifier side. The task images carry the required engine assets.

## BALROG MiniHack task selection

| Native task | Native action limit | Agent observation |
|---|---:|---|
| MazeWalk 9×9 | 200 | 9×9 crop, status and message |
| MazeWalk 15×15 | 1000 | 9×9 crop, status and message |
| Corridor R3 | 1000 | 9×9 crop, status and message |
| CorridorBattle Dark | 350 | 9×9 crop, status and message |
| Quest Easy | 500 | 9×9 crop, status, message and inventory |
| Quest Medium | 1000 | 9×9 crop, status, message and inventory |
| Boxoban Medium | 400 | Native premapped display and status |
| Boxoban Hard | 400 | Native premapped display and status |

Quest exposes the native inventory labels and descriptions. Each native action index has a unique name, with `RUN_*` names for the uppercase compass actions. The client specification maps names to native keycodes so a program can select the item letter requested by the engine.

Each Boxoban task ships one official board as its simulator dataset. Medium uses puzzle 0 from [medium/train/000.txt](https://github.com/google-deepmind/boxoban-levels/blob/78011d8c86ad423bfb2e1005012393b4c3c24409/medium/train/000.txt), and Hard uses puzzle 0 from [hard/000.txt](https://github.com/google-deepmind/boxoban-levels/blob/78011d8c86ad423bfb2e1005012393b4c3c24409/hard/000.txt). The task digests cover these Apache-2.0 assets. The adapter points the native loader at the frozen board, bypasses Gymnasium's seed-forwarding reset check and initializes the goal set before NLE's first terminal check. Native Boxoban then records the real fountain positions during reset. The native four-way controls and shaped rewards remain active. Scoring uses the native outcome and records shaped return separately.

## Coding-agent interface audit for Room and River (suite 0.1.2)

The execution path remains Harbor's native Codex agent -> GameClient -> isolated game service -> MiniHack Adapter. The task's fixed instruction.md is the task prompt; no additional prompt wrapper or model-action parser is added. Agent programs may submit multiple actions, but each service call still advances one native action. There is no direct-LLM or RL entry point.

| Boundary | Native behavior / public evaluation behavior |
|---|---|
| Environment | gym.make(env_id) with no constructor overrides; Room is the native fixed-start/fixed-goal variant, River retains native generation |
| Initialization | NLE core/display seeds, no reseeding, and simulator calendar are frozen evaluation conditions, not native defaults |
| Observation | The default ten native arrays become JSON lists; no additional state descriptions or native pixel observation |
| Action | Direction names map to the indices of native.actions; no new action or action chunk is added to the engine |
| Feedback | Public observe/step returns observation, step, done, steps_remaining and time_left_s; status returns step/done. Native reward, info and individual ending flags remain internal |
| Score | Current suites use 100 points for native success and 0 for valid failure. The public done flag indicates that the session closed |
| Ending | Native outcomes are kept; timeout/agent exit close the evaluation without fabricating native terminated/truncated flags |
| Images | frame() is a character transcript for audit, not native pixel input and not automatically shown to the model |
| Deliverable | The live episode is graded. Neither the final chat reply nor an agent-written result file supplies the score |

Source checks use the pinned MiniHack minihack/envs/room.py, envs/river.py, navigation.py and base.py, plus NLE 1.1.0 env/base.py and env/tasks.py. Suite 0.1.2 clarifies the prompt and adds boundary regression coverage; it retains the 0.1.1 runtime images, native settings, initial hashes and public feedback. Earlier model runs remain attached to their original task digests and prompts.

## Task instructions (suite 0.1.28)

The Room and River instruction.md files follow the upstream coding-agent layout: goal, rules, client example, observation/action reference, external-material policy, resources and time limit. Compatibility and audit explanations live in this README rather than in the agent prompt. The simulator calendar is documented here and in the frozen configuration; it is not needed in the agent task instructions.

The client generates a request ID when `step(action, expected_step)` is called. An explicit `request_id` supports recovering a lost response. Resending the same ID, action and step number returns the cached original response without advancing the game again. `observe()` reads the current state.

The frozen seed/calendar, one-episode no-reset policy and outer resource/time budgets are evaluation conditions, not MiniHack defaults. Native constructor settings, action mapping and internal reward/end-state handling are described above. The audit video is a rendered character transcript, not the native pixel observation or extra model input. Timeout or agent exit seals the current episode without fabricating native ending flags. The final chat reply has no required format, and agent-written output files do not supply the score.

Suites 0.1.2 through 0.1.22 used native return as the main score. Each run retains the task instructions and digest recorded at launch, including the 0.1.2 DeepSeek Room run.

Author new standard game instructions using [the authoring guide](../../../docs/templates/game-standard/README.md) and [the instruction template](../../../docs/templates/game-standard/instruction.md.template). Suite 0.1.4 follows the RoboTwin standard layout more closely and adds a compact observation field reference. It does not add a solution, require a policy file, or change the runtime interface.

Suite 0.1.6 removes runtime topology, protocol labels, grading/recording implementation, redundant execution guidance and unused status-method documentation from the agent instructions. It retains the goal, scoring incentives, observation decoding, action/feedback contract, retry safety and actual restrictions. The open-network paragraph is shortened without changing permissions. Common generated resource and deadline instructions remain intact.

Suite 0.1.7 adds short comments to the client examples explaining observation reads, tool output, the done check and reuse of the returned observation. Runtime behavior is unchanged.

Suite 0.1.8 puts the client example comments next to the relevant calls, following the RoboTwin style. The comments explain the action schema, observation reads and the fields returned by step().

Suite 0.1.9 refines the Room example comments to identify the action count, map dimensions, player coordinates, and action response next to the relevant calls.

Suite 0.1.10 documents Room's observation sizes, one snapshot per response, and the service clock versus the agent deadline. The audit recorder captures the initial state and each executed action and encodes the replay at 6 fps. The public client supplies the native observation arrays to the agent.

Suite 0.1.11 adds a map decoding example, coordinate axes, and guidance for terminal snapshots and stale step numbers in Room. Its generated deadline note distinguishes the session budget from the service countdown.

Suite 0.1.12 organizes Room's rules in the RoboTwin standard style, with short labels for reset access, visible state, budgets, live scoring and observation handling.

Suite 0.1.13 explains how the 5×5 room and the player coordinates fit inside the native 21×79 map observation.

Suite 0.1.14 states the Room success condition as stepping onto the staircase tile and explains how to index the full map using player coordinates.

Suite 0.1.15 lists Room's client return fields and gives examples of the values a controller reads before and after an action.

Suite 0.1.16 follows RoboTwin's field access examples and HumanoidBench's method table. Room shows how to read the returned data and carry the updated step count into the next action.

Suite 0.1.17 clarifies that Room exposes the native NetHack map display and its player-centered crops. The display follows NetHack's sight and memory rules. The native observation configuration is the same as in suite 0.1.16.

Suite 0.1.18 documents the observed native outcome on action 100 and the public client's retry semantics. A reference route that reaches the staircase at the limit is recorded as aborted. A repeated request ID with the original payload returns the original response.

Suite 0.1.19 adds a Room scoring section with a formula and verified examples for success and action-limit failures.

Suite 0.1.20 states the score range when Room uses all 100 actions. The examples show the primary score and success separately, including an episode that reaches the staircase at the limit.

Suite 0.1.21 distinguishes the scoring term `stalled_actions` from the public native NetHack turn counter in `blstats[20]`.

Suite 0.1.22 describes the Room's visible starting scene, how the agent controls the character, and the event that completes the task.

Suite 0.1.23 uses `completion_score` for both Room and River. Blocked actions still use the action budget. The scorer determines points solely from the native success outcome. Earlier runs retain their `native_return` metric and original task digests.

Suite 0.1.24 moves optional request retry details out of the Room and River instructions. The instructions show the usual action call and direct the agent to read the current observation if a response is lost.

Suite 0.1.25 folds the client and observation tables into annotated Python examples and short paragraphs. Both examples show how to decode the map and index the player's tile.

Suite 0.1.26 makes Room's coding-agent workflow explicit. The agent may parse observations, plan and execute multiple actions in a program, then inspect output and revise the program within the same episode. The main script is saved at /app/output/gen.py in the already-collected output directory for audit. The score comes from the live episode.

Suite 0.1.27 expresses Room's program control, script retention and explicit observation viewing as short Rules entries following the upstream task instructions.

Suite 0.1.28 gives Room a crop-only map interface. The task instructions decode `chars_crop` and use `[4][4]` for the player's tile. The DeepSeek Room run from suite 0.1.27 used `native-observation-v1` and retains its original snapshot.

Suite 0.1.29 refreshes the Room and River image pins to the MiniHack files image shared with `minihack-balrog`. Room and River keep their previous seeds, observation profiles and native settings.

The game-only publication also includes Room privileged. Suite 0.2.2 corrects the standard Room README twin declaration; native instances, observations and grading are unchanged.
