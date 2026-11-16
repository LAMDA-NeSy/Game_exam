# MiniHack · MiniHack-Boxoban-Hard-v0

**Task.** Push all four boulders onto the four fountains. A boulder moves one square when you walk into it and the square behind it is clear.

## Rules
- **Drive the character with a program.** Use the Python client below. Your program may run multiple actions in a loop.
- **One episode.** Stop when `done` is true. The native action limit is 400 calls, including accepted actions that leave you in the same cell. See the time limit below.
- The service grades the live episode. Leave your main control script at `/app/output/gen.py` for the record.
- The client returns Python objects. Print the fields you want to inspect through your tools.

## Scoring
A native success earns **100 points**. An episode that ends without success earns **0 points**.

## Client (`/app/game_client.py`)

```python
from game_client import GameClient

game = GameClient()
spec = game.spec()
print(spec["action_schema"]["enum"])        # exact action names for this task
obs = game.observe()                        # current snapshot without spending an action
if not obs["done"]:
    for row in obs["observation"]["chars"]:  # 21 rows of 79 character codes
        print("".join(map(chr, row)))

# Choose an action shown by spec() and use the current step number.
# obs = game.step("E", expected_step=obs["step"])
```

The board uses the native NetHack display. `@` marks the player, the backtick marks a boulder, and `{` marks a fountain. Remember fountain locations when a boulder covers them.

Each accepted action returns an updated observation and step number. Read the new observation before deciding what to do next. If a response is lost, call `observe()` to get the current step and map.

## External material
You may install packages, read installed code, and use public tools and pretrained controllers. Note any external resources used. Do not look up or download a ready-made solution to this exact task, including reference solutions. Network access is open.

## Resources
Your container: **1 CPUs**, **1 GiB of memory**, **256 processes and threads** and **2 GiB** of disk (new files under `/app`, `/tmp` and `/root`). Your container has no GPU. The simulator runs in its own container and does not count against these. CPU only slows you down; a process that goes over any other cap can be killed. Usage and caps: `/run/rcb-limits/usage.json`.

## Time limit
You have 600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.

This is wall-clock time from the start of your session; the time you wait for the simulator service counts. When it is up you are stopped without warning and the episode is graded as it stands at that moment. The service's `time_left_s` counts the same limit from your first request to the service, so it never runs out before your time does: your real time left is `time_left_s` minus the time you spent before that request. Plan by it. Your session started when you received this task. `/run/rcb-limits/usage.json`, rewritten every few seconds, gives the time left on this limit (`time_left_s`) and its end (`deadline_utc`), counted from a little before your session started, so it never gives you more time than you have: read it (or run `date`) before you decide that time is short, never guess. Waiting counts too: a tool call that sends input to a process that keeps running (an interactive interpreter, a simulator loop, a server) can wait for the whole wait or yield time you give it even when the answer is printed at once, so give such calls a short wait and poll again if the output is not complete, or run one-shot scripts that exit when they are done. Installing packages is not cheating (`## External material` above).
