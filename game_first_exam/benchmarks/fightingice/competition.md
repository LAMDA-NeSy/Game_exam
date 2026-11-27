# DareFightingICE 2026 competition workflow

This is an archive-based **prototype**, separate from the frozen 7.0 KickAI
smoke suite. Harbor writes a controller once; isolated Docker workers run that
frozen code in subsequent matches. The stock engine owns its clock, rounds,
physics and native point/style logs. This is not an official-leaderboard result
and is not registered under `harbor run --game-suite fightingice`.

## Two-model duel

Supply two [single-agent Harbor profiles](../../../configs/harbor/) as JSON.
Each profile runs a separate Harbor job to write one controller with the same
600-second authoring limit and the same generated instruction. Each job makes
one authoring attempt with zero automatic retries. Set credentials in the
environment. Real model profiles can incur API charges.

```bash
FTG=game_first_exam/benchmarks/fightingice
python "$FTG/competition.py" duel \
  --model-a /path/to/model-a.json --model-b /path/to/model-b.json \
  --track rushdown --pairs 1 \
  --release /path/to/DareFightingICE-7.1.zip \
  --resources /path/to/resource-7.1.zip \
  --output /tmp/opencode/ftg-duel-01
```

Run from the repository root with Harbor 0.23.0 installed and Docker running.
The command builds the runtime locally from this checkout. Use a new output
directory on each run. Profiles accept `agents` with exactly one native
agent (`name`, `model_name`, and optional `kwargs`); they cannot override the
task, timeout, verifier, or retry policy.

One pair means two matches with P1/P2 reversed, three rounds per match.
`--pairs N` adds matches without regenerating either controller. The duel
has no MCTS opponent, screen, or audio input: policies receive native
delayed FrameData, control flags, and lifecycle events. The native clock
keeps running. Only the authoring jobs call a model.

`duel-report.json` records per-match and per-round results, total round
points, remaining HP, and standings. A round win earns 1, a draw earns 0.5
per side, and remaining HP breaks points ties; exact ties are shared.
`author-jobs/` retains both Harbor records, and `provenance.json` contains
the two frozen controller hashes. `competition.py summarize RUN_DIR`
rechecks the stored result. A missing controller, failed trial, or invalid
match does not produce standings. Use a separate run for Zoning; do not
combine the tracks or compare these scores to the archived league standings.

## MCTS speedrun

Supply `--model` with a single-agent Harbor profile for an end-to-end model
evaluation. Harbor provides the track-specific instruction and native character
tables. The instruction describes the preferred style and the timed scoring
objective. The model gets one 600-second attempt to write `controller.py`.
The runner snapshots the verified submission once and uses it in all ten
matches. A failed authoring trial stops the run before any match and keeps the
Harbor records. The same command accepts frozen `NAME=CONTROLLER_DIRECTORY`
entries in place of `--model`.

```bash
FTG=game_first_exam/benchmarks/fightingice
python "$FTG/competition.py" run --track rushdown --league speedrun \
  --model /path/to/model-profile.json \
  --release /path/to/DareFightingICE-7.1.zip \
  --resources /path/to/resource-7.1.zip \
  --output /tmp/opencode/ftg-speedrun-rushdown
python "$FTG/competition.py" summarize /tmp/opencode/ftg-speedrun-rushdown
```

Use `--track zoning` with a new output directory for Zoning. Run `plan`
with `entry=/path/to/controller` to preview the frozen schedule. Model
runs retain the rendered `instruction.md`, its SHA256 and the native
`author-jobs/` records. Controllers use delayed FrameData and the native
control flag. The runner builds the current bridge locally and runs controllers
offline with screen and audio omitted.

Each entry plays five three-round matches on each side against `MctsAi23i`
in GARNET Rushdown or `MctsAiZoning` in NEZ Zoning. Run the tracks separately.
Wins and draws by remaining HP count their elapsed game frames, including
rounds decided on timeout. Each loss counts 4,200 frames. For example, a
900-frame win, a 3,600-frame draw, and a loss count 8,700 frames and average
2,900 frames. Ranking uses the average across all 30 rounds. Exact ties share
a rank.

`league-report.json` records standings, wins, draws, losses, penalty rounds,
per-round HP and frames, and average scored frames and seconds. The seconds
are calculated at 60 game frames per second. The output includes native
replays, the frozen schedule and controller hashes. The profile
`speedrun-mcts-framedata-v1` uses the archive's speed arithmetic with a single
track-specific baseline. These are Game Exam scores under this profile.
`summarize` independently checks the native evidence and requires all ten
matches per entry.

## What is preserved

Sources: [published rules](https://github.com/TeamFightingICE/FightingICE/blob/v7.1/DareFightingICE/AI/README.md),
[results archive](https://www.ice.ci.ritsumei.ac.jp/~ftgaic/index-R.html),
and [7.1 release](https://github.com/TeamFightingICE/FightingICE/releases/tag/v7.1).
The archive's `2026AI/log/point-style/com_calc.py` has SHA256
`29887c5a8ede9d294f1d698b5d5a833a96b3fc8161475350559d290eedb52390`.
The archive contains result CSVs, replays and entrant archives, not an exact
engine bundle or an organizer controller. Entrant code is not executed by this
workflow unless explicitly provided by the operator in a controller bundle.

| Item | Coverage |
|---|---|
| Engine | Stock 7.1 release/assets are SHA256-pinned; no Java patches. The rules list 7.0 but require NEZ, added in 7.1. Archive CSV headers match 7.1 style logging; exact event binary is unverified. |
| Tracks and clock | GARNET Rushdown and NEZ Zoning, 400 HP, three rounds, original real-time clock (no `--input-sync`). Headless mode, separate container transport and resource/timeout limits are Game Exam choices. |
| Standard League | Round-robin among supplied entries and baselines, two matches per pair with sides reversed. Archive scorer awards one point for higher remaining HP (also on timeout) and half for a tie, then compares total remaining HP. The published rules' prose mentions KO; the archive arithmetic is used instead. Exact ties remain ties; display order is alphabetical. |
| Style stage | Ten matches per entrant per opponent, five on each side. The archive used both organizer and the track MCTS baseline; the published summary names MCTS. Archive-only baseline calibration games are not replayed for scoring new entrants. |
| Style metrics and speed | Native per-frame trackers produce the style CSV; the report averages native columns separately. The archive records elapsed frames for wins/draws and charges 4200 frames for a loss in the speed calculation. No final weighted Style ranking or Formula One league-points formula is asserted: the archive does not supply a reproducible combination, including the treatment of exact ranking ties. |
| Official baselines | `MctsAi23i.jar` and `MctsAiZoning.jar` are in the pinned official resource archive. Full mode requires the operator-supplied `organizer` bundle; provenance records its hash, not an assertion of authenticity. `--mcts-only` is an explicitly partial schedule. |
| Controller API | Native `pyftg` objects, round/game callbacks and native `Key`/`CommandCenter`. Delay and `is_control` come from the engine. The bridge forwards native `AudioData` when present but does not recreate the official generative sound setup or offer visual input. Undelayed state, spectator and match-management messages stay private. |
| Coding Agent | Harbor checks the entry artifact, not a league score. No LLM or model API runs inside the official match phase. Sources are copied and hashed before the first match. The program is read-only and offline during each match. |

Every contestant gets its own network-disabled container and a point-to-point
Unix socket, with a read-only root filesystem and submission mount. The native
management socket is bound to loopback in the trusted engine container. The
engine receives player inputs through the bridge. It writes native logs and
result evidence to mounts outside the contestant containers. A separate
network-disabled verifier reads the engine's CSV and callback evidence
read-only before a match enters the league report. A controller
disconnect, bridge timeout, missing native evidence, or callback/CSV mismatch
fails the league run instead of publishing an invented score.

The authoring container can reach the configured model provider over the
network. Harbor collects the submission and compiles it in a separate
network-disabled verifier before the runner prepares the offline matches.

## Local usage

From the repository root, use Python 3.12+ and Docker on Linux/AMD64.
Build the runtime image locally. Download `DareFightingICE-7.1.zip` and
`resource-7.1.zip` from the official release into a directory outside the
repository. The runner verifies both archive hashes before use; neither is
bundled or republished.

The 7.1 runner requests 1 CPU, 1 GiB of memory, and a 128-process limit for
each engine, controller, and match-verifier container. The same requests
apply on a server. Host quotas and concurrent load can affect how quickly
controllers respond to the real-time engine. Check the effective Docker
limits on the server and keep the resource settings and concurrency
consistent across runs you plan to compare.

```bash
FTG=game_first_exam/benchmarks/fightingice
docker build -f "$FTG/competition.Dockerfile" \
  -t game-exam:fightingice-competition "$FTG"

python "$FTG/competition.py" author /tmp/opencode/fightingice-author \
  --resources /path/to/resource-7.1.zip
# With an existing Harbor agent profile:
harbor run -c /tmp/opencode/fightingice-author/author-job.json -c /path/to/agent-profile.json \
  --jobs-dir /tmp/opencode/fightingice-author-jobs --job-name author-01
```

The author artifact is the trial's `artifacts/app/output/` directory with
`controller.py` and its modules. You may use a locally written controller
directory instead. To inspect the exact match list before running:

```bash
python "$FTG/competition.py" plan --track rushdown --league standard \
  --mcts-only entry=/path/to/artifacts/app/output

python "$FTG/competition.py" run --track rushdown --league standard \
  --mcts-only --release /path/to/DareFightingICE-7.1.zip \
  --resources /path/to/resource-7.1.zip --output /tmp/opencode/ftg-match-01 \
  entry=/path/to/artifacts/app/output
```

Run `--track zoning` separately. Use `--league style` for repeated P1/P2
matches. Add other `NAME=DIRECTORY` entries for a round-robin; use
`--organizer /path/to/organizer` **instead of** `--mcts-only` for the
two-baseline schedule. A real-time match can take over three minutes.

The run directory preserves the full schedule, image and controller hashes,
per-match native evidence, and `league-report.json` for a complete schedule.
`python "$FTG/competition.py" summarize RUN_DIR` rechecks the native CSVs against
the verified match records. Partial MCTS-only results stay explicitly marked.

## Verification

The focused regression is `python game_first_exam/tests/test_fightingice_competition.py`
in a Python 3.12 environment with the benchmark's pinned requirements. Status
of actual launch and evidence verification is recorded in the repository
validation notes.
