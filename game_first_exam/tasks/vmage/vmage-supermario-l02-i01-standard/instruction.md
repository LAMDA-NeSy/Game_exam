# V-MAGE · SuperMario L2

You control Mario in a side-scrolling view. The scene can contain platforms, coins, and enemies.

**Task.** Move and jump to earn as many points as you can before the episode ends. Use the Python client below to act on the screenshots.

## Rules

- **Drive the game with a program.** You may call the client repeatedly in a loop. Leave your main control script at `/app/output/gen.py`.
- **One episode.** There is no reset, restart, or undo. Stop submitting actions when `done` is true.
- **End of play.** Play ends on death, such as a fall or a fatal enemy collision, or when the game applies the frame limit. The episode is also closed at the session time limit.
- **Action limit.** The native frame counter has a limit of 1000, including the initial frame. The game checks the counter after updating Mario, so the last update can still earn points.

## Scoring

Each coin collected, coin awarded by a coin box, or enemy defeated earns **100 points**. The grade uses the accumulated game points, including points earned on the final update. The on-screen `TIME` counter follows game updates. Use the separate wall-clock budget in **Time limit**.

## Client (`/app/game_client.py`)

```python
from game_client import GameClient

game = GameClient()
spec = game.spec()                         # interface settings, no action
print(spec["action_schema"]["enum"])       # case-sensitive action names
print(game.status())                       # accepted step count and done, without fetching an image

obs = game.observe()                       # one screenshot, no action
print(obs["step"], obs["done"], obs["time_left_s"])
game.save_image(obs, "/app/output/view.png") # save the PNG to inspect with your tools

# Choose an action from the listed names based on the screenshot.
# if not obs["done"]:
#     obs = game.step(action, expected_step=obs["step"])
#     game.save_image(obs, "/app/output/view.png")
```

### Observations

`obs["observation"]["image_png_base64"]` holds one 480 × 360 PNG screenshot encoded as base64. Save and inspect the image with your tools, or decode it in your program. Screenshots are returned to your program. Choose which ones to inspect or store. The public observation provides pixels, with no separate object coordinates or score field.

### Actions and feedback

`LEFT` and `RIGHT` move Mario. `UP` requests a jump. `UP+LEFT` and `UP+RIGHT` jump with direction. `NONE` releases movement and jump input. Mario can still coast or fall. Each accepted action repeats for up to 5 native frames and returns one screenshot. Game physics pauses between requests. The session wall clock keeps running.

`observe()` and `step()` both return `observation`, `step`, `done`, `steps_remaining`, and `time_left_s`. `step` counts accepted client actions. `steps_remaining` is `None` because the service adds no separate action cap. A final response can include the last captured screenshot. Use `done` to decide when to stop.

Pass the current `step` as `expected_step`. An unknown action or stale step raises `ValueError` without advancing play. If an action response is lost or your step number is stale, call `observe()` before choosing the next action.

## External material
Network access is open. You may consult general documentation and install general-purpose packages. Use the public Python client and its observations for all information about this episode, including any positions or motion you estimate from screenshots.

Do not obtain or use this exact task’s solutions, reference actions, replays, or hidden level data. This restriction also applies to material available online. Do not inspect the simulator or verifier, read private game files, access hidden state, change the game, or start another episode.

## Resources
Your container: **1 CPUs**, **1 GiB of memory**, **256 processes and threads** and **2 GiB** of disk (new files under `/app`, `/tmp` and `/root`). Your container has no GPU. The simulator runs in its own container and does not count against these. CPU only slows you down; a process that goes over any other cap can be killed. Usage and caps: `/run/rcb-limits/usage.json`.

## Time limit
You have 600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.

The wall-clock budget starts with your session and includes service startup, model thinking, waiting and tool execution. The game advances only when an accepted action is executed; waiting does not advance game physics or pause the wall-clock budget. At the cutoff the live episode is sealed and graded at its current native score. Use `deadline_utc` and `time_left_s` in `/run/rcb-limits/usage.json` for the agent deadline. The client's `time_left_s` counts from the first `observe()` or accepted action; `spec()` does not start that clock.
