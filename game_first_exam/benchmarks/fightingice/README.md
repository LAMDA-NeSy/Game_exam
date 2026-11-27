# FightingICE standard integration

The existing `fightingice` suite below is the frozen 7.0 smoke suite. For the
separate 2026 archive-based controller-authoring and league runner, see
[Competition workflow](competition.md). Its scores are not smoke-suite scores.

This integration evaluates Harbor coding agents controlling DareFightingICE 7.0
through its native Python player interface (pyftg 2.3). The selected observation
is the native delayed FrameData plus is_control, not pixels and not the
non-delay audit state. Native public structured fields are retained, including
positions, actions, remaining frames and projectiles. JSON is only the wire
representation of the native Python data.

The initial scope is ZEN versus the deterministic B-button KickAI example,
with a separate task for each player side. These are smoke configurations, not
the official tournament or a claim of competitive difficulty. The upstream
example is https://github.com/TeamFightingICE/pyftg/blob/e18af08769b02b021bb823fba01f15850aa88c05/examples/KickAI.py.

The native --input-sync option pauses the simulator until both players return
their keys. One public action sends one native Key; observations never release
the waiting player. There is one match, three rounds, 400 initial HP per side,
and the native 3600-frame round limit. Automatic round transitions are native;
the agent cannot reset or launch a second match. Initialization preserves the
native empty delayed observations rather than advancing through them silently.

## Isolation and scoring

The engine and both Python player callbacks run in the trusted sim. SERVER_HOST
is explicitly 127.0.0.1: the native launch, player, spectator and close channels
must not be reachable from the agent container. Only the common HTTP service is
public. The agent image contains neither engine resources nor verifier files.
Raw non-delay state is used only for audit fingerprints and score evidence.

The primary score is 100 times native round wins divided by three. Native round
outcomes compare remaining HP, including a native timeout. Unfinished rounds
give no win credit; success additionally requires a completed match with more
wins than losses. The engine has no scalar Gym reward: adapter Transition reward
is zero, explicitly not a native return. Frame fingerprints cover available
native state, callbacks and counters, not a complete JVM checkpoint or proof of
trajectory replay. No native seed API is claimed; the frozen seed identifies
the configuration, and the first opponent has no RNG.

The native engine assigns random UUIDs to attacks, including initial attacks.
Public observations preserve those native identifiers. Internal fingerprints
canonicalize identifiers by first occurrence within each snapshot, retaining
alias relationships but not claiming byte-identical raw observations across
runs. UUID generation is not a seeded gameplay randomization API.

## Native differences and packaging

The clock is synchronous, not the official wall-clock competition. No external
LLM runner, model gateway, fine-tuned model or generative sound agent is used.
The profile is structured-state-only; lightweight mode disables graphics and
audio generation without changing native combat. Audit frames are a labelled
state transcript, not native game pixels or an additional agent observation.
Original frame delay, commands, combat dynamics and round transitions are kept.

The release and installed files are hash pinned by install_native.py/SOURCE.json.
Downloads and extracted game binaries stay outside this public checkout. pyftg
is MIT; the game resources retain their upstream terms (Dimps assets). No game
binary or art is vendored and no registry publication is implied. Redistribution
permissions for upstream resources remain to be confirmed before publication.

## Local verification

With Python 3.12 and Java 21 installed, install requirements.txt into a separate
environment. Native binaries and downloaded archives belong outside the checkout:

```sh
python game_first_exam/benchmarks/fightingice/install_native.py /tmp/fightingice-native
FIGHTINGICE_HOME=/tmp/fightingice-native python game_first_exam/tests/test_fightingice.py --native
harbor run --game-suite fightingice --standard --list
```

The installer also accepts --engine-archive, --resources-archive or
--resources-dir to reuse local upstream downloads. It checks the release hash
and each installed ZEN resource, and runtime verifies the installed files again.
The resource archive includes unused graphics/audio and can be slow to download.
Only the two pinned ZEN parameter files are installed for this profile.

Docker/Harbor execution requires a daemon kernel supported by Harbor's network
isolation. In Harbor 0.23.0 the kernel probe requires CONFIG_NFT_FIB_INET=y/m
when /proc/config.gz exists. A working `docker version` alone is insufficient.

The frozen 7.0 task requests the same container limits on every host. Both
`main` and `sim` request 1 CPU and 1 GiB of memory, with process limits of
256 and 128 respectively. The host's resource quotas and concurrent load
determine how much capacity the containers actually get. After moving to a
server, run the smoke check there and inspect `runtime-images.json` for the
CPU, memory, and PID settings Docker applied. See the
[7.1 competition limits](competition.md#local-usage) for duel and speedrun.

With a supported kernel:

```sh
harbor run --game-suite fightingice --standard -c configs/harbor/oracle.json \
  --plugin game_harbor:GameRecords --job-name fightingice-oracle
harbor run --game-suite fightingice --standard -c configs/harbor/nop.json \
  --plugin game_harbor:GameRecords --job-name fightingice-nop
python game_first_exam/tests/check_fightingice_result.py jobs/fightingice-oracle oracle
python game_first_exam/tests/check_fightingice_result.py jobs/fightingice-nop nop
```

## Initial container validation (2026-11-17)

Docker Desktop 29.9.3 with containerd storage built the frozen native, agent and
verifier images. The common container tests (55) and native FightingICE tests
(8) passed; the native tests used 1 CPU, 1 GiB and a 128-process limit. The
runtime used the pinned Java 21.0.2, Python 3.12.10 and pyftg 2.3.

A probe inside the real Harbor agent container confirmed that public HTTP and
the declared observation work while the actual random native engine port is
unreachable. Engine/verifier files were absent; the base agent image also had
no reference controller. No public reset was available.

The initial Harbor runs executed both oracle matches (10800 inputs each) and
both zero-input nop controls and collected trusted finals, recordings and
monitor records. The original WSL kernel 5.15.167.4 lacked CONFIG_NFT_FIB_INET.
Harbor correctly rejected the separate verifier's no-network policy: those
four trials were infrastructure failures, not completed scored trials.

As a supplemental check, the collected evidence was graded using the unchanged
tests/test.sh in separate `docker run --network none` verifier containers. Oracle
scores were 100/100 and nop scores 0/0. All four recordings decoded and their last
frames were nonblank audit transcripts. Resource records were present, with
resource_monitor_missing=0 and resource_enforced=0. These checks do not replace
Harbor's missing native verifier results or establish resource enforcement.

The strict check_fightingice_result.py rejected those incomplete jobs. Their
temporary /tmp evidence was subsequently cleared by the WSL restart; the
historical findings above are retained. The complete native rerun below resolves
the original host limitation. See [validation notes](../../../docs/VALIDATION.md).

The two agent Dockerfiles use the official Debian HTTPS endpoints and bounded
download retries after local HTTP package downloads returned timeouts/503s.
The collector artifact declaration is normalization-idempotent and contains one
monitor artifact. No model calls or image publication were performed.

## Complete native Harbor rerun (2026-11-17)

After upgrading to WSL 3.0.5.0 / kernel 6.18.58.1, CONFIG_NFT_FIB_INET=m and
Harbor 0.23.0's kernel probe returned True. Fresh frozen copies were prepared
from the same task configurations; no network policy was relaxed.

| Job | P1 score | P2 score | Inputs per trial |
|---|---|---|---|
| fightingice-oracle-kernel618-01 | 100 | 100 | 10800 |
| fightingice-nop-kernel618-01 | 0 | 0 | 0 |

All four native Harbor trials finished with no exception or infrastructure
error. The independent native verifiers produced their own reward.json files;
check_fightingice_result.py passed for both jobs, including complete provenance,
actual runtime-image capture and derived game reports. Nop outcomes are valid
unfinished failures, not simulator faults. No supplemental grading replaced
these native results.

The live agent/sim probe again confirmed separate network namespaces, public
HTTP access, no reset, no hidden engine/verifier files and an unreachable native
control port. Harbor applied its own no-network policy to the separate verifier
through the native egress sidecar. All four videos decoded completely and had
nonblank audit-transcript last frames. Resource records were present in all
trials (resource_monitor_missing=0); resource_enforced remained 0. Docker's
configured CPU/memory/PID limits were captured separately in runtime-images.json.

The new records and frozen task copies are under
`/tmp/opencode/fightingice-rerun-20261117/`. A hash-verified 144-file backup is in
Docker volume `game-exam-fightingice-validation-20261117-kernel618-01`, directory
`/fightingice-rerun-20261117`, with `/manifest.json` listing file hashes. This
backup survives WSL /tmp cleanup; native records are preserved without rewriting
their original paths. Common container tests (55), Harbor configuration tests
(17) and static checks for all 46 tasks passed again after the upgrade. These
are reference/no-op checks, not model benchmark scores; no model was called.
