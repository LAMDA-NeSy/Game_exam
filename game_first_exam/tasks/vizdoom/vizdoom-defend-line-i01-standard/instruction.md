# ViZDoom · Defend the Line

You can turn and shoot at monsters approaching from across the room. The game replenishes your ammunition.

**Task.** Defeat as many monsters as you can while you are alive. Use the Python client below.

## Rules
- **Drive the game with a program.** You may read observations and run multiple actions in a loop.
- **One episode.** There is no reset or undo. Stop submitting actions when `done` is true.
- **Use the public client and its observations.** Save the control scripts you execute under `/app/output/`.
- **Limits.** Death or the wall-clock deadline ends the episode. The scenario has no fixed native tic limit.

## Scoring
Your score is the native return, which adds 1 per kill and subtracts 1 on death.

## Client (`/app/game_client.py`)
```python
from game_client import GameClient

game = GameClient()
spec = game.spec()
print(spec["actions"])                     # valid button combinations, including "noop"
obs = game.observe()                       # current snapshot without advancing the game
print(obs["step"], obs["done"])
data = obs["observation"]
if data["frame_available"]:
    game.save_image(obs, "/app/output/view.png")

# Syntax example. Choose an action from the current observation.
# if not obs["done"]:
#     obs = game.step(action, expected_step=obs["step"], tics=1)
#     game.save_image(obs, "/app/output/view.png")
```

### Observations
When `observation["frame_available"]` is true, `observation["image_png_base64"]` contains one 320×240 first-person RGB frame encoded as a PNG. Save it with `game.save_image()` to view the PNG with an image tool or analyze it in your program. Frames are returned to your program and do not appear in your context automatically. The engine may return no frame when the episode ends.

### Actions and feedback
Choose a command from `spec["actions"]`. A combination is written in the listed button order, with names joined by `+`. Use `"noop"` to advance without pressing any buttons.

Pass a positive integer as `tics` to hold the action. It defaults to 1. The engine can stop an action early at episode end or the server's time limit. The game stays still between actions.

`observe()` and `step()` return `observation`, `step`, `done`, `steps_remaining` and `time_left_s`. `step` counts accepted actions. `steps_remaining` is `None` because the service adds no action-count limit. `time_left_s` measures the service clock. Per-action rewards are not returned.

Pass the current `step` as `expected_step`. If the step is stale or a response is lost, call `observe()` before choosing another action.

## External material
You may read the public client and use general-purpose libraries. Network access follows the run's allowlist, including for package installation. Solve the task using the live episode. Do not access scenario assets or maps, hidden engine state, other game instances, or solutions, rollouts or trained policies specific to this task.

## Resources
Your container: **1 CPUs**, **1 GiB of memory**, **256 processes and threads** and **2 GiB** of disk (new files under `/app`, `/tmp` and `/root`). Your container has no GPU. The simulator runs in its own container and does not count against these. CPU only slows you down; a process that goes over any other cap can be killed. Usage and caps: `/run/rcb-limits/usage.json`.

## Time limit
You have 600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.

The wall-clock budget starts with your session and includes service startup, planning and tool execution. At the cutoff the episode is graded as it stands. Use the `deadline_utc` and `time_left_s` fields in `/run/rcb-limits/usage.json` to track the session deadline. The client's `time_left_s` counts from the first `observe()` or accepted action, whichever comes first. `spec()` and `status()` do not start that clock.
