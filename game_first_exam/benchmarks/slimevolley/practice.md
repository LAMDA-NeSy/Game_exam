# SlimeVolleyGym · Pixel match with practice

You control the slime on the right. The computer controls the left slime. Both players start with five lives.

**Task.** Use practice matches to learn SlimeVolley and build a controller. Your saved controller plays the scored match after practice. Make the ball land in the left court to score.

## Rules
- **Drive the player with a program.** Your program may call the client in a loop.
- **Two practice scenarios.** You start in `A`. You may restart either `A` or `B` with the client within the same practice budget.
- **Save a practice controller early.** Save a working script at `/app/output/practice_gen.py` and improve it during practice. Both controller files must run on a fresh match with the public observe and action calls. Restart practice with the client before running a controller.
- **One scored match.** Save your final controller at `/app/output/gen.py`. After practice the evaluator selects `gen.py`, or `practice_gen.py` if the final file is missing. It copies only the selected file into a fresh container and runs it once with `python3 /app/gen.py`. The scored match uses a hidden seed different from both practice seeds, so the serve and ball paths may differ. The scored match cannot be restarted.
- **Match limit.** A match ends when either side runs out of lives or reaches 3,000 frames. Stop when `done` is true.

## Scoring
When the ball lands in the left court, the computer loses one life and you score +1. When it lands in the right court, you lose one life and score −1. Your score is the sum of those points, from −5 to +5. Only the scored match counts.

## Client (`/app/game_client.py`)

```python
from game_client import GameClient

game = GameClient()
print(game.spec()["action_schema"]["enum"])       # accepted action names
obs = game.observe()                             # current frame without spending an action
game.save_image(obs, "/app/output/view.png")       # save the frame for inspection

# During practice, restart either "A" or "B" and get its opening frame.
# obs = game.request("/practice/start", {"slot": "B"})

# Choose an action from the frame. "left" illustrates the call.
# if not obs["done"]:
#     obs = game.step("left", expected_step=obs["step"])
```

### Observations
`observe()` and `step()` return one 168×84 RGB PNG in `observation["image_png_base64"]`.

The coins in the upper right show **your** remaining lives. The coins in the upper left show the **computer's**. Five lives show four coins. Each life lost removes one coin until none remain. One life and zero lives both show zero coins.

### Actions and feedback
Use `left` to move toward the net or `right` to move toward the outer wall. `left_jump` and `right_jump` add a jump to those moves. `jump` jumps vertically and `idle` advances a frame without player input.

Each accepted action advances one frame and returns the updated `step` and `done`. The game waits between actions. Pass the current `step` as `expected_step`. If a response is lost or your step is stale, call `observe()` before choosing your next action.

## External material
Use the live matches and general-purpose tools. Do not look up or use ready-made controllers, reference trajectories, recorded demonstrations, or pretrained SlimeVolley weights. The practice network reaches model APIs and approved package registries.

## Resources
Your practice container has **1 CPU**, **1 GiB of memory**, **256 processes and threads**, and **2 GiB of disk** for new files under `/app`, `/tmp`, and `/root`. It has no GPU. The simulator runs separately. Check `/run/rcb-limits/usage.json` for usage and caps.

The scored container has Python's standard library, NumPy, and Pillow. Each controller file can be up to 256 KiB. Include all helper code and parameters in the file. The script can reach the game service only.

## Time limit
You have **600 seconds** of wall-clock time to learn in practice and save your controller. Save a working version before long experiments. Waiting and tool execution count. Check `time_left_s` and `deadline_utc` in `/run/rcb-limits/usage.json` for your session deadline.

Your controller has **120 seconds** in the scored match. If there is no selected script, the selected script is invalid, or it stops early, the game uses `idle` for the remaining frames.
