# Crafter · Survival · Realtime

Control one character in Crafter's procedurally generated survival world. Explore, gather resources and craft tools to unlock the native achievements. The primary score is the fraction of the 22 native achievements reached. Making a wooden pickaxe is also reported as a binary milestone; it does not end the game or replace the primary score.

**Drive the character with a program.** Write your controller in `/app/output/gen.py`, inspect the returned images, and schedule native actions. Nothing is put into your context automatically. The environment is initially paused; the first accepted `submit()` starts its clock. After that it advances **one native action every 0.2 wall-clock seconds**, even while you think or run other code. When your action plan runs out, it executes native `noop` actions until another plan arrives or the episode ends.

You have one episode and no resets. Native death or the native 10,000-action limit ends the episode. Exiting your agent session or reaching the wall-clock cutoff seals the live result. Submit no further actions once `done` is true. No action file is required for grading.

**Your model turns are too slow to drive each tick.** Run a controller that keeps observing and scheduling actions while you use your turns to inspect its log and improve it. Pillow and NumPy are installed for pixel processing. View saved PNGs with your image tool; saving an image alone does not show it to you. Build a working controller and reserve time to execute it and inspect feedback.

## Client (`/app/realtime_client.py`)

```python
import time
from realtime_client import GameClient

client = GameClient()
spec = client.spec()                       # request budget runs; the game is still paused
print(spec['action_schema']['enum'])        # the native Crafter action names
print(spec['timing']['wall_s_per_control_step'])  # 0.2
obs = client.observe()                     # {'step': 0, 'done': False, 'running': False, ...}
client.save_image(obs, '/app/output/view.png')  # save the native 64×64 RGB image for inspection

def execute_plan(actions):                  # call with actions chosen by your controller
    reply = client.submit(actions)           # schedule the plan; returns immediately
    print(reply['start_step'], reply['plan_end_step'])  # first and last scheduled tick
    time.sleep(0.2)                          # the world keeps advancing during this wait
    obs = client.observe()                   # current image and step; does not pause the world
    client.save_image(obs, '/app/output/view.png')
    return obs                              # inspect feedback before choosing the next plan

print(client.status())                     # step, done, running, planned_steps, time_left_s; no image
```

Defining `execute_plan` does not start the episode; your controller must call it with its chosen action list. Continue controlling the live episode while time remains; a final text answer does not execute a plan.

Use this module through Python imports; it has no command-line interface. `observe()` returns `step`, `done`, `running`, `planned_steps`, `time_s`, `time_left_s`, `preparation_s`, `clock_s` and `observation`. The observation contains `image_png_base64`, the native 64×64 RGB image encoded as PNG: the local world view and the inventory/vital-stat icons below it. No extra symbolic map, inventory or privileged state is supplied. `step` counts executed actions, including automatic `noop` ticks.

`submit(actions)` accepts a list of 1–128 native action names. By default it replaces the remaining plan starting on the next tick. `submit(actions, at=n)` starts at the specified absolute tick, at most 128 ticks ahead; the whole plan must fit in that window. Elapsed ticks are dropped, and `late_steps` reports how many. A completely late plan, an unknown action or an oversized plan raises `ValueError` without changing the existing plan. Use `observe()` to check progress before planning again. This asynchronous interface does not use `expected_step` or synchronous `step()`.

`submit()` acknowledges a scheduled plan: its actions have not necessarily run yet. Wait until `step` reaches `plan_end_step` (or `done`) before treating the whole plan as executed. A later plan can replace pending actions. Even an executed action may fail to gather, place or craft because native conditions were not met; check the next image rather than recording success merely because a request was accepted.

The native `move_left/right/up/down` actions set facing and attempt to move one tile. `do` interacts with the object or material directly ahead (such as gathering, attacking or drinking). `place_*` places ahead and requires resources and suitable unoccupied terrain; `make_*` requires resources and the appropriate nearby crafting station. `sleep` rests until recovered or disturbed, and `noop` does nothing while the world and survival needs continue to advance. Use `spec['action_schema']['enum']` for exact accepted names.

## Running your controller

In `/app/output/gen.py`, implement your own `choose_actions(obs)` and use a loop like this. The policy is yours; the loop only shows scheduling and feedback:

```python
import json, time
from realtime_client import GameClient

client = GameClient()
while True:
    obs = client.observe()
    if obs['done']:
        break
    with open('/run/rcb-limits/usage.json') as f:
        if json.load(f)['time_left_s'] <= 1:
            break
    actions = choose_actions(obs)             # implement this: 1–128 native action names
    reply = client.submit(actions)            # accepted, not yet completed
    print('plan', reply['start_step'], reply['plan_end_step'], actions, flush=True)
    while True:
        status = client.status()
        if status['done'] or status['step'] >= reply['plan_end_step']:
            break
        time.sleep(0.02)                      # wait in code; no extra model turn needed
```

Run it in the foreground if the tool session stays open until the episode ends, or start it in a separate process session so it can continue after the launching tool call returns:

```python
import subprocess
from pathlib import Path

with open('/app/output/run.log', 'a') as log:
    proc = subprocess.Popen(
        ['python', '-u', '/app/output/gen.py'], cwd='/app',
        stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
Path('/app/output/controller.pid').write_text(str(proc.pid))
print('controller PID:', proc.pid)
```

In a later tool call, check that the PID still exists (`os.kill(pid, 0)`) **and** that `run.log` and the game's `step` keep advancing. Inspect errors if progress stops; stop an existing controller before starting a replacement so two programs do not overwrite each other's plans. Keep model tool waits short while the controller runs. The game ends normally even if the controller continues to exist; it must stop submitting when `done` becomes true.

The service's `time_s` counts from your first request (including `spec()`), and `time_left_s` is the service budget minus that time. `preparation_s` counts the interval before your first accepted plan; `clock_s` counts how long the game has been running since that plan. Reading observations does not advance the initially paused game; once started, reading and thinking do not pause it. The outer deadline includes time before the first request too: use `/run/rcb-limits/usage.json` for actual session time remaining.

## External material
The network is open. You may install packages (pip, apt), and you may search for, download and use public tools, robot models and pretrained controllers: finding existing work and adapting it to this task is encouraged. Say in your notes what you used. You may read anything installed in your container, this benchmark's own source code included. The one thing not to look up is a ready-made solution to this exact task, such as this benchmark's reference solutions. This is an honour rule; trials are reviewed.

## Resources
Your container: **1 CPUs**, **1 GiB of memory**, **256 processes and threads** and **2 GiB** of disk (new files under `/app`, `/tmp` and `/root`). Your container has no GPU. The simulator runs in its own container and does not count against these. CPU only slows you down; a process that goes over any other cap can be killed. Usage and caps: `/run/rcb-limits/usage.json`.

## Time limit
You have 600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.

The wall-clock budget starts with your session and includes startup, planning and tool execution. At the cutoff the live episode is sealed and graded. The simulator starts advancing only after the first accepted action plan; its `time_left_s` counts from the first request, including `spec()`, so preparation after that request counts toward the service budget. Use `/run/rcb-limits/usage.json` for the outer session deadline. After the clock starts, waiting and model thinking do not pause the game.
