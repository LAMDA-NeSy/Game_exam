# Pac-Man: 600 points

GameWorld's pinned `23_pacman` browser snapshot. An agent controls Pac-Man with four arrow keys and RGB screenshots. The native score must reach 600 before the native game-over screen. Ghost movement and collisions stay native; a game over terminates with reward zero. The adapter freezes browser time between 500 ms input intervals. The score is read from the native GameWorld API, not OCR or agent output.

This is an integration task based on the first GameWorld score threshold, not a claim of reproducing the GameWorld leaderboard. The source is https://github.com/gameworld-project/GameWorld-Games/tree/e5ddb16df85b91a1d17bb0577621cc7c5e65d738/benchmark/23_pacman ; see `RIGHTS.md` in that directory.

Local integration status: static game checks pass. The `pacman-files` OCI digest is calculated from the local sources but has not been published to GHCR. A native Chromium replay, successful oracle, failed contrast run and both demo recordings are still required before this branch can be submitted.
