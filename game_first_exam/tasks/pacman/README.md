# Pac-Man: 600 points

Score 600 in GameWorld's Pac-Man using native RGB screenshots and keyboard moves. A game over or action limit scores zero. Five original GameWorld task presets cover score thresholds; this integration freezes the first threshold.

Run from the repository root (the pinned files image is assembled locally): `harbor run --game-suite pacman --standard -a oracle -y`.

| Replay | Native result |
| --- | --- |
| [600-point clear](../../../docs/demos/pacman/600-point-clear.mp4) | 600 points, success |
| [Ghost collision](../../../docs/demos/pacman/ghost-collision.mp4) | 120 points, game over |

For a first viewing, the [annotated clear](../../../docs/demos/pacman/explained-clear.mp4) and [annotated failure](../../../docs/demos/pacman/explained-failure.mp4) identify the player, pellets, ghosts and the 600-point task goal. The raw replays above preserve the game display without added text. Reaching 600 completes this frozen task; it does not clear the entire maze.
