# PettingZoo Chess · Standard Match

You play White from the standard chess starting position against a fixed computer opponent. Use the Python client to win the game.

## Rules

- Use a program to read the board and submit moves. Your program may make several decisions in a loop.
- You have at most 128 decisions and cannot reset the game. Stop when `done` is true.
- A native win earns 100 points and a native draw earns 50. A loss, illegal move ending or unfinished game earns 0. The played game supplies the score.

## Client (`/app/game_client.py`)

```python
from game_client import GameClient

game = GameClient()
snapshot = game.observe()  # read one snapshot without spending a decision
board = snapshot["observation"]
print(board["board_ascii"], board["legal_moves"])

# Choose an action ID from legal_moves and pass it as a string.
# snapshot = game.step(chosen_id, expected_step=snapshot["step"])
```

`board_ascii` shows ranks 8 through 1 and files a through h. `board_fen` is the full public position in FEN format. `legal_moves` maps action ID strings to absolute UCI moves, including promotion suffixes. `move_history_uci` lists all played moves, and `last_round_moves` lists the latest actions with actor, ID and move.

The enhanced observation includes the original white-view 8×8×111 Boolean tensor (`native_observation`) and 4,672-entry integer `action_mask`, both as JSON lists. Use `legal_moves` to select an action. An ID from `"0"` through `"4671"` outside the current legal set ends the game. An invalid action string outside that ID set is rejected before play advances.

A step plays your move and, if the game continues, one Black move. The response contains one updated snapshot. `step` counts accepted White decisions and `steps_remaining` counts the remaining decisions. `time_left_s` is the service countdown in seconds from the first observation or accepted action. If a response is lost or the step is stale, call `observe()` before choosing your next action. A terminal snapshot can retain native mask entries. Always check `done` before moving.

## External material
You may use public tools, including chess engines and rule libraries. Do not obtain a precomputed answer for this specific benchmark instance or access private evaluator files.

## Resources
Your container: **1 CPUs**, **1 GiB of memory**, **256 processes and threads** and **2 GiB** of disk (new files under `/app`, `/tmp` and `/root`). Your container has no GPU. The simulator runs in its own container and does not count against these. CPU only slows you down; a process that goes over any other cap can be killed. Usage and caps: `/run/rcb-limits/usage.json`.

## Time limit
You have 600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.

This is wall-clock time from the start of your session; the time you wait for the simulator service counts. When it is up you are stopped without warning and the episode is graded as it stands at that moment. The service's `time_left_s` counts the same limit from your first request to the service, so it never runs out before your time does: your real time left is `time_left_s` minus the time you spent before that request. Plan by it. Your session started when you received this task. `/run/rcb-limits/usage.json`, rewritten every few seconds, gives the time left on this limit (`time_left_s`) and its end (`deadline_utc`), counted from a little before your session started, so it never gives you more time than you have: read it (or run `date`) before you decide that time is short, never guess. Waiting counts too: a tool call that sends input to a process that keeps running (an interactive interpreter, a simulator loop, a server) can wait for the whole wait or yield time you give it even when the answer is printed at once, so give such calls a short wait and poll again if the output is not complete, or run one-shot scripts that exit when they are done. Installing packages is not cheating (`## External material` above).
