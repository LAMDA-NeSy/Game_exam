# Crafter integration

Three fixed seeds in a development subset. Unmodified Crafter 1.8.3, default 64x64 RGB observations, 10000-step native episode limit and native action names. The adapter caches reset/step images, serializes observations, translates done/discount, and extracts native metrics. No symbolic grid, recipes or creature-ordering patch. Native object-set traversal can produce different trajectories across processes; this is disclosed rather than changing engine dynamics.

All 22 native achievements and geometric score remain primary. The wooden-pickaxe boolean is explicitly an auxiliary Harbor compatibility flag, not a native win condition. References stop after that milestone and are partial policies. Three inference episodes do not reproduce the original training-budget evaluation.

Run `harbor run --game-suite crafter --standard -a oracle` (or select `--realtime`). Frozen tasks have separate sim, Agent and verifier containers. The wall-clock budget and no-reset trust boundary remain. See [framework](../../../docs/game_framework.md).

Suite 3.1.1 updates only the survival i01 realtime instruction and Agent image: Pillow 10.4.0
and NumPy 1.26.4 are preinstalled for pixel processing, and the instruction explains viewing
saved images and actually calling the asynchronous controller. Native pixels, actions, seed,
scoring, 0.2-second ticks and the 600-second deadline are unchanged. Earlier model runs retain
their original task digests and are not results for this revision. The shared simulator runtime
and adapter are unchanged. Model provider transport belongs to the native Harbor agent profile;
host-specific DNS corrections belong to local environment overlays, not frozen game tasks.

Suite 3.2.0 / realtime execution settings 1.1.0 separate the first-request budget from the
first-submit motion clock, following upstream realtime semantics. The task now documents a
continuous controller, native action meanings and asynchronous feedback. The background launch
uses standard Python `Popen(start_new_session=True)` with detached stdin and redirected output;
it adds no agent wrapper, supervisor, retry policy or reference controller. Model-generated
controllers remain model artifacts. The native environment, pixels, scoring and 600-second
Harbor limit are unchanged. Previous runs keep their old frozen files and timing definitions.

Suite 3.2.1 corrects the generated realtime cutoff paragraph to agree with first-request service timing, and explicitly declares the partial reference-policy evidence on standard tasks. Engine parameters and scores remain unchanged.
