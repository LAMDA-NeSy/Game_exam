# Fireboy and Watergirl in the Forest Temple

This Game Exam task uses GameWorld's original Forest Temple level one. GameWorld 12_01 and 12_02 specify diamond targets. This variant runs all the way to the native successful exit event. Both characters must reach their matching doors. The game reports the diamonds collected as secondary metrics.

Run from the repository root with Docker Desktop running and the project Harbor installation on PATH.

```sh
harbor run --game-suite firewater --standard -a oracle
```

An action advances both roles by six native game updates with the browser clock paused between decisions. The reference solution sends paired actions through GameClient. The verifier checks the native terminal event. A completed episode produces the standard Game Exam replay and final verdict.

- [Pinned upstream task](https://github.com/gameworld-project/GameWorld/blob/84f624bd1e120d30aeebf2eb42a39410e24d3bd4/catalog/tasks/12_fireboy-and-watergirl/12_01.yaml)
- [Pinned game and rights notice](https://github.com/gameworld-project/GameWorld-Games/blob/e5ddb16df85b91a1d17bb0577621cc7c5e65d738/benchmark/12_fireboy-and-watergirl/RIGHTS.md)

The simulator build retrieves the pinned game from upstream. The game assets are downloaded during the simulator build. Oslo Albet retains the game's rights.

## Level one demos and results

| Browser gameplay | Native outcome | Paired moves | Harbor score |
| --- | --- | ---: | ---: |
| [Both characters reach their exits](../../../docs/demos/firewater/level-1-clear.mp4) | `level_completed` | 474 | 1 |
| [Watergirl misses the first lava jump](../../../docs/demos/firewater/level-1-missed-jump.mp4) | `level_failed` | 38 | 0 |

Both Harbor runs returned valid results and zero environment errors. The success run collected all three red and four blue diamonds. The negative control delays Watergirl's first jump while Fireboy follows the reference opening. The clips were recorded separately in the browser. The Harbor recorder stopped before writing a playable MP4.

To reproduce the negative control from the repository root:

```sh
python game_first_exam/tests/benchmarks/firewater/missed_jump/run_harbor.py
```

The control uses a staged task copy with the offline rewarded-ad prompt disabled so the native Game Over menu opens. The agent submits paired moves through the same public client, and the verifier grades the native terminal event.
