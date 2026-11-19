# CoinRun native integration

This change adds the native CoinRun adapter, trusted schema, metric validation, files-only image and native/contract tests. Frozen Harbor tasks and a game suite are intentionally deferred.

## Reference and compatibility

The repository baseline is LAMDA-NeSy/Game_exam commit `7998e10f62811de00a0145ab90480a254a3fc827`. The structural reference is `game_first_exam/tasks/minihack/minihack-room-i01-standard` and its MiniHack backend. Pixel encoding follows the existing Crafter adapter's `image_png_base64` field and shared `encoding.png` helper.

| Area | Implementation |
|---|---|
| Execution | Harbor native agent, existing GameClient, shared runtime/server.py |
| Native backend | ProcgenGym3Env, one environment, one native act per accepted request |
| Observation | Cached native 64×64 RGB image, PNG transport |
| Actions | All 15 native action indices, exposed as enum strings |
| Seeding | num_levels=1, start_level=seed, rand_seed=seed, num_threads=1 |
| Native options | easy/hard, default camera and assets, paint_vel_info=False, use_sequential_levels=False |
| Completion | Native prev_level_complete, native reward 10 on collecting the coin |
| Score | completion_score = 100 × success, existing family_macro reducer |
| Ending | Gym3 first flag after an action maps to one native termination flag |
| Native action cap | 1000 native steps |

## Episode boundary

Gym3 automatically resets the native engine when the first episode ends. The adapter reads the reward and previous-level completion marker at that boundary, seals its own episode and rejects further actions. The shared server also rejects new requests after finalization and handles request deduplication.

The image returned at that boundary belongs to the automatically started episode. The adapter retains the last pre-action image for the terminal snapshot and audit video. That image can be one action older than the terminal event. The completion result comes from the native boundary metadata. This behavior must be documented in the task instruction.

Gym3 exposes one episode-boundary flag. Native death and native timeout are both mapped to terminated=True, truncated=False. No separate death/timeout classification is inferred. Shared wall-clock exhaustion retains its existing budget reason.

## Isolation and audit

Only image_png_base64 is returned in adapter observations. The spec contains the public interface. Full get_info data, level seeds and serialized state stay inside the sim. fingerprint uses native serialized state, cached pixels and episode accounting. At termination that serialized state includes the automatic reset. frame returns the cached public pixels.

The adapter is designed for the existing standard-mode main/sim/verifier boundary. A future frozen task must keep the instance in sim/verifier, expose only the public client to main, and use a separate no-network verifier. No frozen CoinRun task is included in this change.

## Dependencies

requirements.txt pins the Python 3.10 simulator dependencies. Host Harbor and agent/verifier environments retain their existing Python profile. SOURCE.json records the official Linux Procgen wheel digest, and simulator/test base images are digest-pinned. The files-only manifest binds the adapter, schema, metrics and dependency list.

Gym3 requires imageio-ffmpeg 0.3.x. imageio is pinned to 2.19.5 for compatibility with the shared Recorder. Test setup pins setuptools 80.9.0 and wheel 0.45.1.

The CoinRun native-test Dockerfile uses the Tsinghua Debian mirror because the default CDN stalled in the validation environment. APT signature checking remains enabled.

## Validation commands

Run contract tests in a host environment with numpy, Pillow, imageio and imageio-ffmpeg.

```bash
python game_first_exam/tests/test_coinrun_contract.py
```

Run real-engine equivalence in the proposed simulator environment after installing the requirements.

```bash
python game_first_exam/tests/test_coinrun_native.py
```

The native test requires actual Procgen packages and fails on missing dependencies. It compares raw engine state, images, rewards and terminal completion across both modes and three seeds, and checks the 1000-step native timeout. Contract tests use an explicit engine double to exercise shared server and grader behavior. These tests cover the adapter without publishing a frozen task or reference trajectory.

## Sources

- https://github.com/openai/procgen/blob/0.10.7/procgen/env.py
- https://github.com/openai/procgen/blob/0.10.7/procgen/src/games/coinrun.cpp
- https://github.com/openai/procgen/blob/0.10.7/procgen/src/game.cpp
- https://github.com/openai/gym3/blob/master/gym3/libenv.py
- https://pypi.org/project/procgen/0.10.7/
- https://pypi.org/project/gym3/0.3.3/
