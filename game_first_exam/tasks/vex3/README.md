# Vex 3 Act 1

The standard task loads the first numbered act from the pinned GameWorld browser game. The agent sees RGB screenshots and uses movement, jumps, and slides. A deathless finish scores one, and the first death ends the attempt with a score of zero. Checkpoints are recorded as a secondary metric.

The adapter pauses between actions. Once the player lands at spawn, it fixes the 30 Hz Phaser clock phase so the same 64 ms input interval advances the same native updates across runs.

Run the reference and failure control from the repository root.

```sh
harbor run --game-suite vex3 --standard -a oracle -y
python game_first_exam/tests/benchmarks/vex3/missed_jump/run_harbor.py
```

| Replay | Native result |
| --- | --- |
| [Act 1 clear](../../../docs/demos/vex3/act-one-clear.mp4) | Four checkpoints and zero deaths |
| [Missed opening jump](../../../docs/demos/vex3/missed-jump.mp4) | One death |

[Vex 3 source and rights notice](https://github.com/gameworld-project/GameWorld-Games/tree/e5ddb16df85b91a1d17bb0577621cc7c5e65d738/benchmark/30_vex-3)
