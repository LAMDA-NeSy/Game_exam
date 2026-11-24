# Rocket League 2D

Score the first goal against the computer. The first goal ends the episode. A 1–0 score earns one point. Conceding first or reaching the 250-action limit without scoring earns zero.

Read the current RGB screenshot using GameClient.save_image(). Each action holds the controls for 160 milliseconds of game time. The match pauses between decisions. Use wait, left, right, brake, jump, jump_left, jump_right, boost_left, boost_right, jump_boost_left or jump_boost_right.

Use the live service through `/app/game_client.py`:

```python
from game_client import GameClient
game = GameClient()
print(game.spec())
obs = game.observe()
print(obs["observation"])
# obs = game.step(action, expected_step=obs["step"])
```

The public envelope contains step, done, steps_remaining and time_left_s. Each action requires the current expected_step and a request_id; the client creates an ID if omitted. Retry a lost response only with the same ID and identical payload. The service deduplicates it without advancing the environment again. Only spec, observe, status and submit are available. Agent-written output files do not determine scores.

## External material
The network is open. You may install packages (pip, apt), and you may search for, download and use public tools, robot models and pretrained controllers: finding existing work and adapting it to this task is encouraged. Say in your notes what you used. You may read anything installed in your container, this benchmark's own source code included. The one thing not to look up is a ready-made solution to this exact task, such as this benchmark's reference solutions. This is an honour rule; trials are reviewed.

## Resources
Your container: **1 CPUs**, **1 GiB of memory**, **256 processes and threads** and **2 GiB** of disk (new files under `/app`, `/tmp` and `/root`). Your container has no GPU. The simulator runs in its own container and does not count against these. CPU only slows you down; a process that goes over any other cap can be killed. Usage and caps: `/run/rcb-limits/usage.json`.

## Time limit
You have 600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.

This is wall-clock time from the start of your session; the time you wait for the simulator service counts. When it is up you are stopped without warning and the episode is graded as it stands at that moment. The service's `time_left_s` counts the same limit from your first request to the service, so it never runs out before your time does: your real time left is `time_left_s` minus the time you spent before that request. Plan by it. Your session started when you received this task. `/run/rcb-limits/usage.json`, rewritten every few seconds, gives the time left on this limit (`time_left_s`) and its end (`deadline_utc`), counted from a little before your session started, so it never gives you more time than you have: read it (or run `date`) before you decide that time is short, never guess. Waiting counts too: a tool call that sends input to a process that keeps running (an interactive interpreter, a simulator loop, a server) can wait for the whole wait or yield time you give it even when the answer is printed at once, so give such calls a short wait and poll again if the output is not complete, or run one-shot scripts that exit when they are done. Installing packages is not cheating (`## External material` above).
