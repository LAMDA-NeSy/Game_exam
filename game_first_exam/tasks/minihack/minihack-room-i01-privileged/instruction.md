# MiniHack · Room 5×5 · Privileged

Move the NetHack character (`@`) onto the down staircase (`>`) in a lit 5×5 room. There are no monsters or traps. Moving onto `>` wins; no separate descend action is needed.

**Work with a program.** The native environment runs in your container. You may inspect the installed code and `session.env`, reset freely, and try alternative plans. Nothing is put into your context automatically: print or save whichever observations your code needs. Keep your main script at `/app/output/gen.py`.

**Submit `/app/output/actions.json`.** Save the actions from your chosen episode with `session.save()`. The evaluator runs that sequence from the frozen initial state in a fresh, separate environment. Your local state, claimed score and final chat message do not determine the score. A successful replay earns **100 points**; an unsuccessful, missing or invalid submission earns **0**.

## Python interface

Run your script with `/app/minihack_python /app/output/gen.py`. This launcher prepares the native MiniHack process.

```python
from privileged import Session

session = Session()                       # creates one native environment at the starting state
obs = session.observe()                    # {'step': 0, 'done': False, 'observation': {...}}
print(session.spec()['action_schema']['enum'])  # N, E, S, W, NE, SE, SW, NW
for row in obs['observation']['chars']:     # native 21×79 terminal canvas
    print(''.join(map(chr, row)))
print(obs['observation']['blstats'][:2])    # absolute [column, row] of the character

# Choose directions using the observation, then execute them in your program:
# obs = session.step('E')                  # returns the updated snapshot; one accepted action
# obs = session.reset()                   # returns the initial snapshot and clears saved action history
# session.env                             # the local native Gymnasium environment, available for inspection

session.save()                            # writes the current episode's actions to /app/output/actions.json
session.close()                           # releases the native environment
```

The 21×79 array is the NetHack display canvas containing the 5×5 room, not a 21×79 traversable room. Native visibility and memory still determine the displayed cells. `observation` contains the complete native arrays, including the 9×9 character-centered crops, `blstats` and `message`.

Use `session.step()` to record the actions you intend to submit. Calling `session.env.step()` directly does not update the saved action list. Resetting starts the same frozen instance again and discards the previous action list; save the chosen episode before exiting.

Each direction counts as one native action, including blocked movement. At most 100 actions may be submitted. Native MiniHack truncates on action 100, even if that move reaches the staircase, so success must occur earlier. Do not submit actions after `done` becomes true. The wall-clock limit covers all experiments and resets; it is not renewed by `reset()`.

## External material
The network is open. You may install packages (pip, apt), and you may search for, download and use public tools, robot models and pretrained controllers: finding existing work and adapting it to this task is encouraged. Say in your notes what you used. You may read anything installed in your container, this benchmark's own source code included. The one thing not to look up is a ready-made solution to this exact task, such as this benchmark's reference solutions. This is an honour rule; trials are reviewed.

## Resources
Your container: **1 CPUs**, **1 GiB of memory**, **256 processes and threads** and **2 GiB** of disk (new files under `/app`, `/tmp` and `/root`). Your container has no GPU. CPU only slows you down; a process that goes over any other cap can be killed. Usage and caps: `/run/rcb-limits/usage.json`.

## Time limit
You have 600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.

This is wall-clock time from the start of your session; the time a simulator takes to start counts. When it is up you are stopped without warning and only what is in `/app/output/` at that moment is graded, so save a deliverable as soon as you have one and overwrite it whenever you have a better one. Your session started when you received this task. `/run/rcb-limits/usage.json`, rewritten every few seconds, gives the time left on this limit (`time_left_s`) and its end (`deadline_utc`), counted from a little before your session started, so it never gives you more time than you have: read it (or run `date`) before you decide that time is short, never guess. Waiting counts too: a tool call that sends input to a process that keeps running (an interactive interpreter, a simulator loop, a server) can wait for the whole wait or yield time you give it even when the answer is printed at once, so give such calls a short wait and poll again if the output is not complete, or run one-shot scripts that exit when they are done. Installing packages is not cheating (`## External material` above).
