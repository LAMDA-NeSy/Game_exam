# MiniHack · MiniHack-River-v0

Cross the river and reach the down staircase (`>`). Use the Python client below.

## Rules
- One episode, no reset or undo; at most 350 actions. Stop when `done` is true.
- No output file is required.

## Scoring
You earn **100 points** if MiniHack registers success by stepping onto `>` before the action limit and time cutoff. An episode that ends without success earns **0 points**.

## Client (`/app/game_client.py`)
```python
from game_client import GameClient

game = GameClient()
spec = game.spec()                         # interface settings
print(spec["action_schema"]["enum"])       # ['N', 'E', 'S', 'W', 'NE', 'SE', 'SW', 'NW']
obs = game.observe()                       # current snapshot without spending an action
if not obs["done"]:
    data = obs["observation"]              # native observations as JSON lists
    for row in data["chars"]:               # 21 rows of 79 character codes
        print("".join(map(chr, row)))       # show the decoded map in tool output
    x, y = data["blstats"][:2]              # column, row from the display's top-left
    print(chr(data["chars"][y][x]))         # player's tile, normally '@'

# Replace "E" with a direction chosen from the map.
# if not obs["done"]:
#     obs = game.step("E", expected_step=obs["step"])  # one action, one updated snapshot
```

### Observations
The snapshot is symbolic. In `chars`, `@` marks the player, `.` is floor and `>` is the down staircase. The arrays `glyphs`, `colors` and `specials` give symbol IDs, colors and display flags. All four display arrays also have 9×9 player-centered `_crop` versions. `message` gives the game message as character codes padded with zeros.

### Actions and feedback
`step()` executes one action and returns the same fields as `observe()` (`observation`, `step`, `done`, `steps_remaining` and `time_left_s`). `step` counts accepted actions and `done` marks the end of the episode. `steps_remaining` is `None` because the service adds no cap beyond the native 350-action limit. Per-step rewards are not returned.

Pass the current `step` as `expected_step`. If the step number is stale or the action response is lost, call `observe()` before choosing your next move.

## External material
You may install packages, read installed code, and use public tools and pretrained controllers. Note any external resources used. Do not look up or download a ready-made solution to this exact task, including reference solutions. Network access is open.

## Resources
Your container: **1 CPUs**, **1 GiB of memory**, **256 processes and threads** and **2 GiB** of disk (new files under `/app`, `/tmp` and `/root`). Your container has no GPU. The simulator runs in its own container and does not count against these. CPU only slows you down; a process that goes over any other cap can be killed. Usage and caps: `/run/rcb-limits/usage.json`.

## Time limit
You have 600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.

This is wall-clock time from the start of your session; the time you wait for the simulator service counts. When it is up you are stopped without warning and the episode is graded as it stands at that moment. The service's `time_left_s` counts the same limit from your first request to the service, so it never runs out before your time does: your real time left is `time_left_s` minus the time you spent before that request. Plan by it. Your session started when you received this task. `/run/rcb-limits/usage.json`, rewritten every few seconds, gives the time left on this limit (`time_left_s`) and its end (`deadline_utc`), counted from a little before your session started, so it never gives you more time than you have: read it (or run `date`) before you decide that time is short, never guess. Waiting counts too: a tool call that sends input to a process that keeps running (an interactive interpreter, a simulator loop, a server) can wait for the whole wait or yield time you give it even when the answer is printed at once, so give such calls a short wait and poll again if the output is not complete, or run one-shot scripts that exit when they are done. Installing packages is not cheating (`## External material` above).
