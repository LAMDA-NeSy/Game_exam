# Pac-Man: 600 points

GameWorld's pinned `23_pacman` browser snapshot. An agent controls Pac-Man with four arrow keys and RGB screenshots. The native score must reach 600 before the native game-over screen. Ghost movement and collisions stay native; a game over terminates with reward zero. The adapter freezes browser time between 500 ms input intervals. The score is read from the native GameWorld API, not OCR or agent output.

This is an integration task based on the first GameWorld score threshold, not a claim of reproducing the GameWorld leaderboard. The source is https://github.com/gameworld-project/GameWorld-Games/tree/e5ddb16df85b91a1d17bb0577621cc7c5e65d738/benchmark/23_pacman ; see `RIGHTS.md` in that directory.

The 24-action reference route reached 600 points on the unmodified pinned browser game at seed 42. A stationary control ended in native game over at 120 points. Both browser runs were recorded. The `pacman-files` OCI digest was calculated locally but has not yet been published to GHCR. The Harbor oracle scored 1.0 in 24 actions with 600 points and zero deaths; the 78-action ghost-collision control scored 0.0 with 120 points and one game over. Both verifier records were valid and reported zero environment errors (2026-11-24).
