# Rocket League 2D
GameWorld task 25_01 asks the player to score without conceding. This adapter ends the match at its first goal and checks both native goal counters. The simulator builds the original single-player game from its pinned upstream commit and uses its default AI. Only screenshots and player-one keyboard actions cross the client interface.

Run the reference attack and the early-release control from the repository root.

```sh
harbor run --game-suite rocketleague --standard -a oracle -y
python game_first_exam/tests/benchmarks/rocketleague/concede/run_harbor.py
```

[GameWorld task](https://github.com/gameworld-project/GameWorld/blob/84f624bd1e120d30aeebf2eb42a39410e24d3bd4/catalog/tasks/25_rocket-league-2d/25_01.yaml) · [Game assets and rights](https://github.com/gameworld-project/GameWorld-Games/tree/e5ddb16df85b91a1d17bb0577621cc7c5e65d738/benchmark/25_rocket-league-2d)

## Gameplay demos

| Player input | Score | Steps | Harbor reward |
| --- | --- | ---: | ---: |
| [Hold boost to the right](../../../docs/demos/rocketleague/first-goal.mp4) | 1–0 | 31 | 1 |
| [Release boost after eight steps](../../../docs/demos/rocketleague/conceded-goal.mp4) | 0–1 | 172 | 0 |

Both Harbor trials completed with zero environment errors. Their FFmpeg recording pipes closed early. The linked videos are separate browser runs of the same policies, with matching opening fingerprints, final scores and action counts.
