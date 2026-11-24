# SlimeVolleyGym

One frozen standard match in native `SlimeVolleyNoFrameskip-v0`. The coding agent controls the right player using native 168×84 RGB frames and the six native discrete controls. The unmodified built-in RNN controls the left side. The host records the match through the shared standard service.

The [pinned Apache-2.0 source](../../benchmarks/slimevolley/SOURCE.json) is installed into the simulator from a hash-checked archive. It uses the native four-value Gym interface and OpenCV headless. The adapter caches native frames, translates the native ending into life exhaustion or the 3000-frame limit, and leaves the separate Harbor wall-clock cutoff to the shared service.

The primary score is native net points. A completed match with positive net points counts as a success. At an earlier cutoff, net points still count. The offline oracle replays a fixed action list generated using the native state-space baseline on the right. It verifies the match, client and grader without representing a pixel policy.

Run `harbor run --game-suite slimevolley --standard --list` to view the frozen task.
