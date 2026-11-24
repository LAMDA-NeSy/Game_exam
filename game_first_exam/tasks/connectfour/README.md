# Connect Four

A frozen PettingZoo Connect Four match against a deterministic defensive opponent.

Red plays first. The native renderer draws the second player's pieces dark gray.
The opponent takes an immediate win, blocks an immediate Red win, then chooses a
deterministic legal column. This is one introductory fixed match, not an established
difficulty ladder. The agent sees the live board and may choose up to 21 columns.

Two scored native previews of the same frozen opening:

- [Red wins, score 1](../../../docs/demos/connectfour/red-win.mp4)
- [Red loses, score 0](../../../docs/demos/connectfour/red-loss.mp4)

The previews use reference and control routes, not a model's policy. Generate them
with `python game_first_exam/tests/benchmarks/connectfour/record_demos.py`.
