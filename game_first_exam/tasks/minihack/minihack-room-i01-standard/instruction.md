# MiniHack · MiniHack-Room-5x5-v0

You control a single NetHack character in a lit 5×5 room. The starting map display shows your character (`@`), the floor (`.`), and the down staircase (`>`). The room contains no monsters or traps.

**Task.** Use the Python client to read the map and choose one of eight compass directions per action. Step onto the staircase before the native action limit. The move onto `>` completes the task without a separate descend command.

## Rules
- **Drive the character with a program.** Use the Python client to read observations and execute actions. Your program may run multiple actions in a loop.
- **No reset or undo.** You get one episode. Stop submitting actions when `done` is true.
- **No privileged state.** Use the symbolic map, player stats and game messages returned by the client.
- **Action and time limits.** Each accepted direction counts as one action, even if blocked. The 100th action exhausts the native limit, even if it reaches the staircase. See `## Time limit` for the separate wall-clock budget.
- The service records your live episode and grades it. Leave your main control script at `/app/output/gen.py` for the record.
- **Nothing is put into your context automatically.** Observations come back as lists in a Python dictionary. What you print, inspect and store is your code's decision.

## Scoring
You earn **100 points** if MiniHack registers success by stepping onto `>` before the action limit and time cutoff. An episode that ends without success earns **0 points**.

## Client (`/app/game_client.py`)
```python
from game_client import GameClient

game = GameClient()
spec = game.spec()                         # interface settings
print(spec["action_schema"]["enum"])       # ['N', 'E', 'S', 'W', 'NE', 'SE', 'SW', 'NW']
print(spec["reset_budget"])                # 0

obs = game.observe()                       # current snapshot without spending an action
print(obs["step"], obs["done"])            # 0 False at the start of a live episode
print(obs["time_left_s"])                  # seconds left on the service clock
if not obs["done"]:
    data = obs["observation"]              # local map, player stats and game message
    for row in data["chars_crop"]:          # 9 rows of 9 character codes
        print("".join(map(chr, row)))       # show the decoded map in tool output
    print(chr(data["chars_crop"][4][4]))    # crop center, normally '@'

print(game.status())                       # {'step': 0, 'done': False} without fetching the map

# Replace "E" with a direction chosen from the map.
# if not obs["done"]:
#     obs = game.step("E", expected_step=obs["step"])  # pass 0 on the first move, then reuse the returned step
#     print(obs["step"], obs["done"])        # 1 False if the first move was accepted and play continues
```

### Observations
`chars_crop` shows four cells in each direction from the character. The lit 5×5 room fits inside the 9×9 crop at the start. The crop moves with the character and follows NetHack's sight and memory rules. Columns increase east and rows increase south.

The matching 9×9 arrays `glyphs_crop`, `colors_crop` and `specials_crop` give symbol IDs, colors and display flags. `blstats` holds 27 player statistics. Its first two entries are the character's absolute map coordinates, while the character is at `[4][4]` in the crop. `message` holds 256 character codes padded with zeros.

### Actions and feedback
The game advances only on actions, with no fixed control rate. `step()` returns one updated snapshot with the same fields as `observe()` (`observation`, `step`, `done`, `steps_remaining` and `time_left_s`). `step` counts accepted actions. `steps_remaining` is `None` because the service adds no cap beyond the native 100-action limit. See `## Time limit` for the two clocks.

Check `done` before using the map or coordinates to plan your next move. `done` can mark either success or failure. The final snapshot can contain cleared coordinates.

Pass the current `step` as `expected_step`. An unknown direction or stale step raises `ValueError` without executing the action. If the step number is stale or the action response is lost, call `observe()` before choosing your next move.

## External material
You may install packages, read installed code, and use public tools and pretrained controllers. Note any external resources used. Do not look up or download a ready-made solution to this exact task, including reference solutions. Network access is open.

## Resources
Your container: **1 CPUs**, **1 GiB of memory**, **256 processes and threads** and **2 GiB** of disk (new files under `/app`, `/tmp` and `/root`). Your container has no GPU. The simulator runs in its own container and does not count against these. CPU only slows you down; a process that goes over any other cap can be killed. Usage and caps: `/run/rcb-limits/usage.json`.

## Time limit
You have 600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.

The wall-clock budget starts with your session and includes service startup, waiting and tool execution. At the cutoff, the episode is graded as it stands. Use `deadline_utc` and `time_left_s` in `/run/rcb-limits/usage.json` to plan around the agent deadline. The client's `time_left_s` counts from the first `observe()` or accepted action, whichever comes first. `spec()` does not start that clock.
