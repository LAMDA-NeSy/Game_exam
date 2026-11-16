# Game execution modes

The first mode integrations reuse Harbor task selection, agent/model configuration, Docker isolation,
collection and native job records. They do not add direct-LLM or RL runners.

| Mode | Initial task | Environment access | Submission and grading |
| --- | --- | --- | --- |
| standard | Existing five benchmarks | Isolated synchronous service | Live episode |
| privileged | MiniHack Room i01 | Native environment inside agent container; inspect and reset | `actions.json`; independent verifier replay |
| realtime | Crafter survival i01 | Isolated service advancing every 0.2 s after first accepted plan | Live episode, including automatic noop ticks |

## Native settings and mode differences

Both new tasks copy their standard twin's frozen instance exactly: engine, seed, native actions,
termination rules and metric specification remain unchanged. `mode.json` separately binds execution
semantics. MiniHack privileged exposes native arrays and local environment access; its results must
not be compared as the same condition as standard's 9×9 crop. The 21×79 native terminal canvas is
not hidden world state, but local inspection is explicitly permitted in privileged mode.

Crafter itself remains a discrete Gym environment. The added scheduler is an evaluation condition,
not a claim that native Crafter has a mandatory 5 Hz clock. Model latency now costs native actions.
The clock starts on the first accepted plan. Empty queue ticks use native noop; discrete commands
are not repeated. Late plans are trimmed/rejected, and request IDs preserve action deduplication.
The outer Harbor deadline includes initial planning. Since realtime settings 1.1.0 the service
budget starts with the first request, including spec/status, matching upstream 2.3. Its motion clock
starts separately at the first accepted plan. `time_s`/`time_left_s` describe the service budget;
`preparation_s`/`clock_s` describe time before/after motion starts. Harbor's existing monitor file
is the authority for session time left; these service fields do not grant a new budget on submit.
The collector freezes the sim before waiting for resource-monitor collection; otherwise log
collection latency would add native actions after the agent finishes. Main-process cleanup still
follows Harbor's native lifecycle.

Controllers use the native agent's shell/Python tools. The Crafter instruction demonstrates
standard `subprocess.Popen(start_new_session=True)` with stdin detached and output redirected,
then checking both its PID and growing progress log from later tool calls. In a local real
Codex 0.167.1 + DeepSeek diagnostic, plain `nohup ... &` stopped after its launching tool call,
whereas the new-session process kept the same PID across two later calls (41 additional
heartbeat records). This is evidence for that pinned harness, not a guarantee about every agent.
There is no supervisor or automatic policy restart; Harbor still stops all task processes at
the agent boundary. Process diagnostics are fixtures, excluded from game evaluation results.

## Implementation

`game_first_exam/runtime/modes/` contains a small separate files image. Existing standard images
stay pinned. `privileged.Session` wraps the existing native adapter and exports actions;
`mode_grade.replay` opens a new instance inside the network-disabled verifier. It never trusts the
agent's local score, engine state or arbitrary executable submission. Missing/invalid actions yield
zero; engine or collection failures remain infrastructure errors.

`realtime_server.Realtime` schedules the existing `Game.submit` in a background thread.
`realtime_client.GameClient` reuses connection readiness and HTTP request handling from the standard
client, replacing synchronous step with asynchronous submit. Observations remain native Crafter RGB.
`realtime.json` records the separate clocks, ticks, automatic noops, late plan steps and scheduler lag. The verifier checks
its mode digest and action count alongside the existing trusted final record.

Harbor retains `config.json`, `lock.json`, trial trajectories and verifier rewards. Privileged replay
video and final state are in the verifier folder; realtime live video/state are collected from the sim.
Videos advance by action frame and do not visualize model thinking time. No new report format is
required. Optional game reports retain the independent replay final and reject mixed-mode aggregation.

## Extending coverage

Do not create mode copies by renaming standard tasks alone. Privileged needs an inspectable local
engine plus independent replay. Realtime needs a defensible clock and idle-action policy. Add a frozen
mode config, task-specific instructions, native equivalence tests and full Harbor validation before
marking another game/mode available. These initial tasks are smoke coverage, not a new official
benchmark protocol or proof of model quality.
