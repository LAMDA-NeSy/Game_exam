# VGC · gen9championsvgc2026regma

You pilot one side of a frozen Pokémon VGC doubles battle (two active Pokémon per side). Your opponent is the native **random** player. Both teams are fixed and revealed (open team sheet). Win the battle.

**Task.** Use the Python client below to read the battle state and submit one joint action per turn. Knock out all four of the opponent's brought Pokémon before yours are knocked out.

## Rules
- **Drive the battle with a program.** Use the Python client to read observations and submit actions. Your program may run many turns in a loop.
- **No reset or undo.** You get one episode. Stop submitting actions when `done` is true.
- **One action advances one turn.** Each `step()` submits the simultaneous choices for both of your active Pokémon.
- The service records your live episode and grades it. Leave your main control script at `/app/output/gen.py` for the record.
- **Nothing is put into your context automatically.** Observations come back as JSON in a Python dictionary. What you print, inspect and store is your code's decision.

## Scoring
You earn **100 points** if your side wins the battle. Any episode that ends without winning earns **0 points**.

## Client (`/app/game_client.py`)
```python
from game_client import GameClient

game = GameClient()
spec = game.spec()                         # interface settings and action grammar
print(spec["action_schema"])               # the accepted action format for this task
print(spec["opponent"])                    # the fixed native opponent

obs = game.observe()                       # current snapshot without spending a turn
print(obs["step"], obs["done"])            # accepted turns so far and whether the episode ended
if not obs["done"]:
    data = obs["observation"]              # battle state serialized as JSON
    print(data)                            # inspect the fields you need

# Replace the example with a real joint action chosen from the observation.
# if not obs["done"]:
#     obs = game.step("...", expected_step=obs["step"])  # one turn, one updated snapshot
```

### Observations
`observation` is the native battle state serialized as JSON. TODO(author): after the adapter's
`observe()` is finalized against poke-env, list here the exact fields the agent receives (active
Pokémon, HP, moves, status, weather, team, etc.) and their encoding.

### Actions and feedback
The action grammar is declared in `spec["action_schema"]["pattern"]`. Each `step()` returns one
updated snapshot with the same fields as `observe()`. `step` counts accepted turns. Pass the
current `step` as `expected_step`; if the step number is stale or a response is lost, call
`observe()` before choosing the next action.

## External material
The network is open. You may install packages (pip, apt), and you may search for, download and use public tools, robot models and pretrained controllers: finding existing work and adapting it to this task is encouraged. Say in your notes what you used. You may read anything installed in your container, this benchmark's own source code included. The one thing not to look up is a ready-made solution to this exact task, such as this benchmark's reference solutions. This is an honour rule; trials are reviewed.

## Resources
Your container: **1 CPUs**, **1 GiB of memory**, **256 processes and threads** and **2 GiB** of disk (new files under `/app`, `/tmp` and `/root`). Your container has no GPU. The simulator runs in its own container and does not count against these. CPU only slows you down; a process that goes over any other cap can be killed. Usage and caps: `/run/rcb-limits/usage.json`.

## Time limit
You have 600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.

This is wall-clock time from the start of your session; the time you wait for the simulator service counts. When it is up you are stopped without warning and the episode is graded as it stands at that moment. The service's `time_left_s` counts the same limit from your first request to the service, so it never runs out before your time does: your real time left is `time_left_s` minus the time you spent before that request. Plan by it. Your session started when you received this task. `/run/rcb-limits/usage.json`, rewritten every few seconds, gives the time left on this limit (`time_left_s`) and its end (`deadline_utc`), counted from a little before your session started, so it never gives you more time than you have: read it (or run `date`) before you decide that time is short, never guess. Waiting counts too: a tool call that sends input to a process that keeps running (an interactive interpreter, a simulator loop, a server) can wait for the whole wait or yield time you give it even when the answer is printed at once, so give such calls a short wait and poll again if the output is not complete, or run one-shot scripts that exit when they are done. Installing packages is not cheating (`## External material` above).
