# SlimeVolleyGym · Pixel match

You control the player on the right. Make the ball land on the left side of the court. The computer controls the left player. Both start with five lives.

## Rules
- Play through the Python client. A program may call it in a loop. Save your main control script at `/app/output/gen.py` for the record.
- You get one match, with no reset or undo. A point costs the side where the ball landed one life. The game serves a new ball between points.
- Each accepted action advances one frame. The world waits for your next action. Play ends when either side runs out of lives or you reach 3000 frames. Stop when `done` is true.

## Scoring
A point won on the left counts as +1. A point conceded on the right counts as −1. Your score is points won minus points conceded, from −5 to +5. Your current score counts at the time limit. A native match ending with a positive score counts as a win.

## Client (`/app/game_client.py`)
```python
from game_client import GameClient

game = GameClient()
print(game.spec()["action_schema"]["enum"])
obs = game.observe()                          # current frame, no action spent
game.save_image(obs, "/app/output/view.png")  # save the RGB frame for inspection

# Choose an action from the image. "left" illustrates the call.
# obs = game.step("left", expected_step=obs["step"])
```

`observe()` and `step()` return one 168×84 RGB PNG in `observation["image_png_base64"]`, along with `step`, `done` and `time_left_s`. Use the returned step number in your next call. If the response is lost or your step is stale, call `observe()` to recover the current frame and step.

The coins at the upper right show your remaining lives. The coins at the upper left show the computer's. Five lives show four coins. One life and zero lives both show zero coins.

Use `left` toward the net or `right` toward the outside wall. `left_jump` and `right_jump` combine movement and jump. `jump` moves vertically, and `idle` advances a frame with no input.

## External material
You may install packages you need (pip, apt), and you may read anything installed in your container, the simulator's and this benchmark's own source code included. Please solve the task yourself: do not search the web for, or download, a ready-made solution to it, such as published or reference solutions, recorded demonstrations, or policies trained for it. This is an honour rule; trials are reviewed. The network reaches your model's API and the package registries (PyPI, Debian / Ubuntu archives) only.

Additional rules for this task (stricter than the above): Use only the live match and general-purpose tools. Do not use task-specific controllers, reference trajectories, or pretrained SlimeVolley weights.

## Resources
Your container: **1 CPUs**, **1 GiB of memory**, **256 processes and threads** and **2 GiB** of disk (new files under `/app`, `/tmp` and `/root`). Your container has no GPU. The simulator runs in its own container and does not count against these. CPU only slows you down; a process that goes over any other cap can be killed. Usage and caps: `/run/rcb-limits/usage.json`.

## Time limit
You have 600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.

The wall-clock budget starts with your session and includes service startup, waiting and tool execution. At the cutoff, the episode is graded as it stands. Use `deadline_utc` and `time_left_s` in `/run/rcb-limits/usage.json` for the session deadline. The client's `time_left_s` starts on the first `observe()` or accepted action. `spec()` and `status()` do not start that clock.
