# Write a DareFightingICE controller

Write a Python controller under `/app/output/`. `controller.py` must export
`AI`, a no-argument subclass of `pyftg.AIInterface`. Put any helper modules
there as well. The evaluation runs your frozen source in a fresh container
without internet access or dependency installation. Python's standard library
and `pyftg` 2.3 are available. Keep the bundle to regular files under 64 MiB.
Native `Motion.csv` and `gSetting.txt` for GARNET/NEZ are available under
`/app/moves/` in matches and during authoring when staged with `--resources`.

{{ROLE}}
Use `initialize(game_data, player_number)` to identify the character and side
(`True` for P1). `get_information(frame_data, is_control)` receives the
engine's delayed `FrameData`, which can be empty at round start, and the native
control flag. The published standard data path is available; no undelayed
state, spectator stream, or engine management calls are provided. {{AUDIO}}
`processing()` updates
your chosen `pyftg.Key`, and `input()` returns it. You can use
`pyftg.CommandCenter` to construct native key sequences where appropriate. The
remaining native callbacks cover initialization, round/match end and cleanup.
Inspect the installed `AIInterface` signatures and types before writing code.

The match clock continues while the controller runs. Each round starts with
400 HP and lasts at most 3600 native frames. {{SCORING}}

Write and compile a working submission within the 600-second authoring
budget. Save a working version before spending time on refinements. Do not
connect to private game services, download ready-made entries, or rely on
network calls during a match.

This Harbor task checks only that the controller entry file exists and
compiles. It does not play a match or assign a league score; that happens
after authoring with the separate native match runner.
