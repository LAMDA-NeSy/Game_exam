# Game-only publication checks — 2026-11-16

This is packaging/migration validation, not a model leaderboard or a claim of benchmark-wide model performance.

- All 44 frozen native instance JSON files match the pre-cleanup development workspace byte for byte.
- All shipped suites pass preflight, source-image digest checks, task normalization, protocol checks, resource declarations, verifier isolation and monitor wiring.
- Shared tests: 52 passed.
- Native adapter environments: MiniGrid 2, Crafter 3, TextWorld 2, Baba Is AI 11, MiniHack 11 passed.
- Native Harbor integration: 17 passed, including game-only default/all selection and root discovery without a robot tree.
- Total regression tests: 98 passed. No paid model calls were made for this publication validation.
- A fresh editable installation in a separate Python 3.12.10 environment resolved Harbor 0.23.0; the documented task-list command and Harbor tests passed there too.
- One native Harbor MiniHack Room standard oracle run completed in 4 actions, primary score 100, native return 1.0, with no Harbor exception or environment/infra error. Video decoded successfully; runtime-image provenance was complete.
- That short oracle trial reported `resource_monitor_missing=1` and `resource_enforced=0`. It is evidence for execution/collection/grading, not evidence of complete resource sampling or enforcement. Do not silently relabel this flag.

Local execution used macOS ARM64 with Linux containers and cached fixed adapter images. The full Harbor trial used a local Docker DNS/build-source overlay; that host-specific file and all job logs remain outside version control. Clean builds on other machines and remote CI are distinct checks, not implied by these local results.

Changes beyond file removal are limited to game-only discovery/packaging and documentation/metadata: the shared connection source moved unchanged; the Crafter realtime generated cutoff paragraph now agrees with its existing first-request service budget; partial Crafter references explicitly describe their evidence; Room's README names its existing privileged twin. Native engine code, instances, actions, rewards and scores were not changed by this publication cleanup.

Robot implementations/assets, old MiniGrid prototype, website source, editor settings, credentials and local jobs are absent from the public file list. The original MIT notice and bundled native-source license notices are retained.

## FightingICE container checks - 2026-11-17

These checks were performed on branch `feat/fightingice-standard`, separately
from the publication validation above. No paid model calls were made.

- Docker Desktop 29.9.3, Compose 5.7.0, Linux AMD64, containerd image store;
  the daemon started with no images. The current shell's stale docker-group
  membership was handled with a new group session, without changing socket modes.
- Native, agent and verifier images built from frozen sources. Java 21.0.2,
  Python 3.12.10 and pyftg 2.3 were used inside the native test image.
- Common tests: 55 passed inside the pinned common container. FightingICE tests:
  8 passed inside its pinned container under 1 CPU, 1 GiB and 128 PIDs (423.250 s).
  Host Harbor configuration/integration tests: 17 passed. All 46 task directories
  passed suite preflight, file-image digests, normalization and isolation checks.
- In the actual Harbor agent container, public HTTP and the declared delayed
  observation worked; the random native control port was blocked. Engine and
  verifier files were absent. The base agent image had no reference solution.
- `fightingice-oracle-03` executed both three-round matches, each with 10800
  inputs and a trusted native final showing three round wins. `fightingice-nop-01`
  collected valid zero-action unfinished finals for both sides.
- Both native Harbor jobs failed at separate-verifier setup: WSL kernel
  `5.15.167.4-microsoft-standard-WSL2` lacks `CONFIG_NFT_FIB_INET`; Harbor 0.23.0's
  kernel probe returned False and refused `network_mode='no-network'`.
  Native trial exceptions and incomplete reports were retained. A zero Harbor
  CLI exit status did not imply that any trial had been graded successfully.
- Supplemental validation ran the unchanged task `tests/test.sh`, including the
  resource verifier, in disconnected Docker containers (`--network none`, only
  loopback present) against collected read-only evidence. Scores: oracle P1/P2
  100/100, nop P1/P2 0/0, with no sim/infra error in these supplemental verifier
  results. None of the native Harbor result/reward files was overwritten.
- All four audit videos decoded completely and had nonblank last-frame images.
  They are labelled native-state transcripts, not native game pixels. Sealed
  resource records were present: `resource_monitor_missing=0`,
  `resource_enforced=0`; do not report monitor enforcement as enabled.
- Initial HTTP Debian package downloads timed out/returned 503. The new task
  agent Dockerfiles now use official Debian HTTPS URLs and bounded retries;
  dependency selection, combat rules and observation permissions were preserved.
  Earlier failed/cancelled jobs were retained for diagnosis during this check.

Initial evidence was outside the public checkout under
`/tmp/opencode/fightingice-docker-20261117/`: native jobs and frozen task copies,
`isolation.json`, and `supplemental-verification.json`. Supplemental grading is
not a substitute for complete native Harbor records. That temporary directory
was cleared by the subsequent WSL restart. At this stage full Harbor validation
was blocked; the historical findings remain above, while the fresh native rerun
below resolves the blocker.

## FightingICE native Harbor rerun - 2026-11-17

- WSL 3.0.5.0, daemon kernel `6.18.58.1-microsoft-standard-WSL2`, Docker Desktop
  29.9.3. CONFIG_NFT_FIB_INET=m; the unchanged Harbor 0.23.0 kernel probe returned
  True. The deleted temporary Python environment was reinstalled from this
  checkout and new frozen copies were prepared from the existing task configs.
- Native job `fightingice-oracle-kernel618-01`: both player-side trials completed
  all three rounds, with 10800 accepted inputs and primary_score=100 each.
- Native job `fightingice-nop-kernel618-01`: both trials completed with valid
  zero-action unfinished failures, primary_score=0, success=0 and no sim error.
- All four trials had exception_info=null and infra_error=0. Their native
  independent verifiers ran under Harbor's unchanged no-network policy and
  generated their own reward.json. No external verifier output was substituted.
  Both jobs passed `game_first_exam/tests/check_fightingice_result.py`, including
  complete game provenance, runtime-images and derived summary checks.
- A live cross-container probe confirmed distinct main/sim network namespaces,
  public GameClient access, reset_budget=0, absent engine/verifier files and an
  unreachable actual native control port. The native network-control sidecar
  was enabled for the separate verifier, not the public agent environment.
- All four audit videos decoded completely and last frames were nonblank.
  Monitor records were present in all native verifier outputs:
  resource_monitor_missing=0, resource_enforced=0. The Docker CPU/memory/PID caps
  were captured in runtime-images.json; monitor enforcement is not claimed.
- Common container tests: 55 passed again. Harbor configuration tests: 17
  passed again. All 46 tasks passed preflight, file-image digest, normalization,
  protocol, isolation and resource checks. The native adapter and task policies
  were not changed for this rerun. No paid model calls were made.

Fresh evidence is in `/tmp/opencode/fightingice-rerun-20261117/`, including
`prepared.tasks/`, the two jobs and `isolation.json`. A second copy is retained
outside the checkout in Docker volume
`game-exam-fightingice-validation-20261117-kernel618-01`, under
`/fightingice-rerun-20261117`; `/manifest.json` records SHA256 hashes for all 144
files. The backup was checked against the source byte for byte and survives
WSL /tmp cleanup. Native config, lock and result paths were not rewritten.

## DareFightingICE 2026 archive-based workflow

This workflow is separate from the frozen 7.0 smoke tasks above.

- Both official 7.1 release archives matched the published SHA256 hashes.
  Their resource bundle contains `MctsAi23i` and `MctsAiZoning`. No archived
  entrant code or model weights were run or republished.
- Archive compatibility checks parsed 90 Standard matches and 160
  entrant-vs-baseline Style matches in each of GARNET Rushdown and NEZ Zoning
  (500 paired point/style records). The Standard archive totals 270 round
  points per track, including half-points on each side of a draw. Per-controller
  Standard points, remaining HP and game counts, and Style speed frames and
  game counts, matched the reviewed archive calculation functions.
- A fresh Harbor 0.23.0 authoring task completed with a reward of 1 for a
  local oracle controller fixture and 0 for `nop`, both with zero exceptions.
  These are artifact checks only, not match scores. No model API was used.
- That same hash-checked controller artifact completed four stock 7.1 matches:
  both sides against `MctsAi23i` in Rushdown and both against `MctsAiZoning`
  in Zoning. All four passed the separate offline verifier, including native
  CSV/callback agreement. The no-op fixture scored zero round points in both
  tracks; each MCTS scored six. The active workers' Docker configuration was
  checked for disabled networking, read-only root and contestant mounts, and
  no access to the engine or results. The two outputs are under
  `/tmp/opencode/ftg-rush-final` and `/tmp/opencode/ftg-zone-final`. These were
  MCTS-only match tests, not full native Style or two-baseline series.
- The competition image built locally. Six focused regression tests passed
  (including socket filtering, archive calculations, ties, and rejection of
  inconsistent callback/CSV evidence); the 46-task preflight, 55 common
  tests, 8 existing native FightingICE tests, and 17 Harbor configuration
  tests also passed.
- The archive does not identify the exact event engine build, include the
  organizer baseline bundle, or provide a complete combined Style ranking
  routine. The official generative sound pipeline is not recreated. The
  implemented profile is therefore archive-based, not an exact reproduction
  of the official leaderboard.

## FightingICE two-model duel

- An end-to-end Rushdown check used two native Harbor Oracle jobs with the same
  local controller fixture. Both authoring checks passed. The frozen controllers
  played two stock 7.1 matches with sides reversed; both matches passed the
  separate verifier. Each side earned 3 points and 1050 total remaining HP,
  sharing rank 1. `summarize` reproduced the saved result.
- Both workers had separate sockets, no network, and read-only submission
  mounts. The controller fixture explicitly rejected audio, screen, and
  undelayed-state callbacks. The `nop` empty-submission check stopped before
  any match and created no report.
- The 46-task static check, 55 common tests, 17 Harbor configuration tests,
  and 8 FightingICE competition tests passed. This local check did not call
  a model API.

## FightingICE MCTS speedrun

- The 46-task static check, 55 common tests, 17 Harbor 0.23.0 configuration
  tests, 8 native FightingICE tests, and 11 focused competition tests passed.
  The new tests cover both tracks' schedules, per-round penalties, shared
  ranks, and rejection of incomplete or inconsistent match evidence.
- A local no-op controller completed all ten native Rushdown matches against
  `MctsAi23i`, five on each side. All 30 losses received the 4,200-frame penalty
  for an average of 4,200 scored frames (70 game seconds). All ten matches
  passed the independent verifier and produced native replays. The saved
  `league-report.json` matched `summarize`, and an earlier check on the
  incomplete run emitted no standings. The evidence is under
  `/tmp/opencode/ftg-speedrun-rushdown-01/`. This run used no model API.

## FightingICE model-to-match workflow

- The speedrun `--model` entry point stages a track-specific prompt, runs
  one 600-second Harbor authoring trial with zero retries, and freezes the
  verified controller. An empty `nop` submission completed its separate
  authoring verifier with reward 0 and produced no match or league report.
- Local Harbor Oracle jobs generated an isolation-check controller for each
  speedrun track. Rushdown and Zoning each completed ten verified matches
  and 30 rounds, with five matches on each side. The fixture lost all rounds
  on both tracks and averaged 4,200 scored frames in each. Both reports
  matched `summarize` and had ten native replay files.
- Two local Harbor Oracle jobs using the same no-op fixture completed the
  two-match Rushdown duel. Each side scored 3 points and 2,400 total remaining
  HP. `summarize` reproduced the saved standings.
- Live Docker inspection confirmed no network access, read-only roots and
  submission mounts, and one private socket per external controller. The
  fixture checked for a loopback-only network and rejected audio, screen,
  and undelayed-state callbacks. Local Oracle jobs made no model API calls.
- The 46-task static check, 55 common tests, 17 Harbor configuration tests,
  8 native FightingICE tests, and 12 competition tests passed.

## FightingICE video export

- The replay exporter recorded four verified 7.1 matches with the native
  graphical engine, including both Rushdown sides, a Zoning match, and a
  duel. The renderer reproduced all twelve original round lengths. FFmpeg
  decoded each 960×640 H.264 video through the end.
- A missing `.dat` produced a failed manifest entry, the next match still
  exported, and the saved league report kept the same SHA256.
- A local browser preview outside the checkout played the videos, switched
  sides and tracks, and displayed the verified round results at desktop and
  mobile widths.
