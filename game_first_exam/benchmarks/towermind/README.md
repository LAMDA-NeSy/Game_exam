# TowerMind adapter

This development integration uses the upstream Unity Linux x86-64 player and the two official TowerMind wrappers. `SOURCE.json` pins the archive and wrapper source by commit and SHA256. The simulator extracts its own copy, selects an original benchmark level and a positive seed, keeps the native 16-step decision interval and selects the native sparse reward. For this pinned player, `IsAutoPlayLevels=0` selects the configured level and `1` cycles levels. Retries are off.

Initialization resets through the TowerMind wrappers after the Gym bridge discovers its agent slots. The player runs in upstream pixel-only mode (`IsOnlyPixelObs=1`). The bridge selects the 512×512 RGB `CameraSensor` by its reported name and dimensions. The public episode starts at the reset observation. The adapter records the first native terminal or interrupted transition and closes the episode.

The public `player-rgb-v1` profile exposes one cached 512×512 RGB player frame as PNG. Actions carry two coordinates in `[-3, 3]` and a native integer action type from 0 through 11 as a string, for example `"-1.5 1.2 2"`. The official wrapper handles native action mapping. The adapter drops any separate text or vector observations before caching the camera frame. Raw step metadata, configuration, seed and fingerprints stay inside the simulator. The fingerprint covers the cached RGB pixels, instance identity and step outcomes.

The pinned sparse reward charges 1 per base breach and 0.005 per reported action outcome. The adapter uses these increments and the configured starting health to track base health. It returns each native reward unchanged. Success requires the first native episode to terminate with the base still alive.

The Python ML-Agents gRPC listener binds to the simulator's own IPv4 loopback. The network test uses independent sim and client images, an internal Docker network and no shared mounts. Its client only carries the shared HTTP client, the connection helper and the probe. Keep those boundaries when packaging a Harbor task. Upstream static assets are public independently of access to the live simulator.

The files-only image carries implementation and dependency inputs. The test image downloads and verifies the original assets at build time. It uses the upstream Colab example's Xvfb screen settings and lets Unity select its graphics backend. The image includes Mesa's software OpenGL and Vulkan drivers. The simulator loads the Gym bridge from the installed ML-Agents distribution directly because the package's Gym registry initializer attempts a remote manifest fetch. A test-only instance drives native equivalence, idle interval and first-episode checks. Benchmark discovery for model evaluation will be added with a frozen task.

Run from the repository root on a Linux Docker host.

```bash
docker build -f game_first_exam/tests/envs/towermind.Dockerfile -t game-tests:towermind .
docker run --rm --network none -v "$PWD:/repo:ro" game-tests:towermind bash game_first_exam/tests/run.sh towermind
docker build --target client -f game_first_exam/tests/envs/towermind.Dockerfile -t game-tests:towermind-client .
bash game_first_exam/tests/check-towermind-network.sh
```
