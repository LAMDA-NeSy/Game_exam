# Connect Four · Red versus Yellow

Play a full game of Connect Four as Red. Drop your tokens into the 7-column board; connect four horizontally, vertically, or diagonally before the fixed Yellow opponent does. The native screenshot draws Yellow's pieces dark gray. The opponent wins immediately when it can, blocks an immediate Red win when it can, and otherwise makes a deterministic legal move.

You may make up to 21 Red decisions. A native Red win scores 1; a loss, draw, illegal column, or unfinished match scores 0. A full column is an illegal move and ends the game. You cannot reset the game.

Use the live service through `/app/game_client.py`:

```python
from game_client import GameClient

game = GameClient()
state = game.observe()
print(state["observation"]["board"])
print(state["observation"]["legal_columns"])
# state = game.step("3", expected_step=state["step"])
```

Actions are the column numbers `"0"` through `"6"` as strings. Each accepted step plays one Red move and, if no one has won, one Yellow move. The observation includes an RGB screenshot (`image_png_base64`), a 6×7 board (0 empty, 1 Red, 2 Yellow), legal columns, recent moves and the outcome. The response also has `step`, `done`, `steps_remaining` and `time_left_s`. Check `done` before moving, and use the current `expected_step` with each action. On a lost response, call `observe()` before submitting another move. Your files do not determine the score.

## External material
The network is open. You may install packages (pip, apt), and you may search for, download and use public tools and pretrained controllers. Do not look up a ready-made solution to this exact task. Say in your notes what you used.

## Resources
Your container: **1 CPUs**, **1 GiB of memory**, **256 processes and threads** and **2 GiB** of disk (new files under `/app`, `/tmp` and `/root`). Your container has no GPU. The simulator runs in its own container and does not count against these. CPU only slows you down; a process that goes over any other cap can be killed. Usage and caps: `/run/rcb-limits/usage.json`.

## Time limit
You have 600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.

This is wall-clock time from the start of your session; the time you wait for the simulator service counts. When it is up you are stopped without warning and the episode is graded as it stands at that moment. The service's `time_left_s` counts the same limit from your first request to the service, so it never runs out before your time does: your real time left is `time_left_s` minus the time you spent before that request. Plan by it. Your session started when you received this task. `/run/rcb-limits/usage.json`, rewritten every few seconds, gives the time left on this limit (`time_left_s`) and its end (`deadline_utc`), counted from a little before your session started, so it never gives you more time than you have: read it (or run `date`) before you decide that time is short, never guess. Waiting counts too: a tool call that sends input to a process that keeps running (an interactive interpreter, a simulator loop, a server) can wait for the whole wait or yield time you give it even when the answer is printed at once, so give such calls a short wait and poll again if the output is not complete, or run one-shot scripts that exit when they are done. Installing packages is not cheating (`## External material` above).
