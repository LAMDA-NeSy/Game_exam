# FightingICE: ZEN versus KickAI

You control P2 ZEN in a two-player fighting game. The other player is controlled
by a fixed opponent. Use the Python client to observe the fight and execute
directional and attack inputs. Play one match of three rounds.

## Rules
- Write and run a controller using the public client. Your program may execute many actions in a loop, and you may inspect feedback and revise it during the same match. Keep your main controller at `/app/output/gen.py`.
- There is no reset, undo, character change or second match. Automatic resets between rounds are part of the game. Stop sending actions when `done` is true.
- Use only the observations returned by the client. Do not connect to internal game interfaces or read hidden state.
- The game waits between actions. Each accepted key combination advances one native input frame. A round ends at a KO or after 3600 native frames. Each player starts each round with 400 HP.
- Observations are returned to your program; print or inspect the parts you need. They are not automatically displayed to the model.

## Scoring
Each native round is won by the player with greater remaining HP; equal HP is
a draw. You earn `100 * rounds_won / 3` points. Draws and unfinished rounds give
no win credit. Winning the match requires completing all three rounds with
more wins than losses. `done` can also mean that a budget or agent session ended.

## Client
```python
from game_client import GameClient

game = GameClient()
spec = game.spec()
print(spec["action_schema"]["enum"])  # legal strings: noop, A, B, ..., BDR, ...
print(spec["native_action_ids"])      # numeric action IDs in FrameData
print(spec["native_state_ids"])       # numeric state IDs in FrameData
reply = game.observe()                # read without advancing the fight
data = reply["observation"]
player = data["player"]               # 0 for P1, 1 for P2
frame = data["frame_data"]
if not frame["empty_flag"]:
    me, opponent = frame["character_data"][player], frame["character_data"][1-player]
    print(me["hp"], me["x"], opponent["hp"], opponent["x"])
if not reply["done"]:
    reply = game.step("noop", expected_step=reply["step"])  # release every key for one frame
    print(reply["step"], reply["done"])
```

### Observations
`frame_data` is the native delayed structured observation, not a screenshot.
It contains `empty_flag`, `current_frame_number`, `current_round`, `front`,
`character_data` and `projectile_data`. The two character entries are always
ordered P1 then P2. Positions use native stage coordinates: x increases right,
y increases down. The stage is 960 by 640.

Character entries include HP, energy, position/bounds, velocity, numeric action
and state, facing direction, remaining action frames and native attack data.
`spec()` supplies the numeric ID tables and static `game_data`. `is_control`
is the native callback flag indicating whether your character can be controlled.
The nominal FrameData delay is 15 frames. At round starts, empty observations
have no character entries; check `empty_flag` before indexing. The callback's
own control flag need not refer to the delayed observation's frame.

### Actions and feedback
`A`, `B`, `C` are attack buttons; `D`, `L`, `R`, `U` are down, left, right and up.
Combine letters once each, in the order `ABCDLRU`, to hold them simultaneously
for one input frame. For example, `AR` means right and A; `noop` releases all
keys. Directions are absolute, not relative to facing. Native input recognition
determines which move executes; sending a key does not guarantee an attack.

`step()` returns the same snapshot fields as `observe()`: `step`, `done`,
`observation`, `steps_remaining` and `time_left_s`. `step` counts accepted input
frames across the match; the delayed native frame counter restarts each round.
`steps_remaining` is null because only the native round limits apply. Invalid
keys and stale step numbers raise `ValueError` without advancing. If a reply is
lost, read the current observation before selecting the next action.

## External material
You may install packages and use public tools. Note external resources used.
Do not obtain a ready-made solution to this exact task. Network access is open.

## Resources
Your container: **1 CPUs**, **1 GiB of memory**, **256 processes and threads** and **2 GiB** of disk (new files under `/app`, `/tmp` and `/root`). Your container has no GPU. The simulator runs in its own container and does not count against these. CPU only slows you down; a process that goes over any other cap can be killed. Usage and caps: `/run/rcb-limits/usage.json`.

## Time limit
You have 600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.

The wall-clock budget starts with your session and includes service startup, waiting and tool execution. At the cutoff, the episode is graded as it stands. Use `deadline_utc` and `time_left_s` in `/run/rcb-limits/usage.json` to plan around the agent deadline. The client's `time_left_s` counts from the first `observe()` or accepted action, whichever comes first. `spec()` does not start that clock.
