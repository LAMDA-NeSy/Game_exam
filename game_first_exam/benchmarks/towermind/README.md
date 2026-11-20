# TowerMind adapter

This development integration uses the upstream Unity Linux x86-64 player and the two official TowerMind wrappers. `SOURCE.json` pins the archive and wrapper source by commit and SHA256. The simulator extracts its own copy, selects an original benchmark level and a positive seed, keeps the native 16-step decision interval, disables automatic level progression and retries, and selects the native sparse reward. Initialization follows the upstream example and resets through the TowerMind wrappers after the Gym bridge has discovered its agent slots. The first playable observation starts the single public episode. The adapter records the first native terminal or interrupted transition and closes the episode.

The public `player-rgb-v1` profile exposes one cached 512×512 RGB player frame as PNG. Actions carry two coordinates in `[-3, 3]` and a native integer action type from 0 through 11 as a string, for example `"-1.5 1.2 2"`. The official wrapper handles native action mapping. Structured observations, raw step metadata, configuration, seed and fingerprints stay inside the simulator. The fingerprint covers the cached native JSON, instance identity and step outcomes. Unity's full state and RNG checkpoint are unavailable.

The Python ML-Agents gRPC listener binds to the simulator's own IPv4 loopback. The network test uses independent sim and client images, an internal Docker network and no shared mounts. Its client only carries the shared HTTP client, the connection helper and the probe. Keep those boundaries when packaging a Harbor task. Upstream static assets are public independently of access to the live simulator.

The files-only image carries implementation and dependency inputs. The test image downloads and verifies the original assets at build time and uses Xvfb with software OpenGL for rendering. The simulator loads the Gym bridge from the installed ML-Agents distribution directly because the package's Gym registry initializer attempts a remote manifest fetch. A test-only instance drives native equivalence, idle interval and first-episode checks. Benchmark discovery for model evaluation will be added with a frozen task.

Run from the repository root on a Linux Docker host.

```bash
docker build -f game_first_exam/tests/envs/towermind.Dockerfile -t game-tests:towermind .
docker run --rm --network none -v "$PWD:/repo:ro" game-tests:towermind bash game_first_exam/tests/run.sh towermind
docker build --target client -f game_first_exam/tests/envs/towermind.Dockerfile -t game-tests:towermind-client .
bash game_first_exam/tests/check-towermind-network.sh
```
