# V-MAGE native bridge (internal research)

The five thin adapters share this bridge. Native code and assets are fetched only
at image build time with `source_loader.py --destination /opt/vmage`. The optional
`--archive` argument accepts an already downloaded copy, but the same pinned
archive SHA256 is always required. SOURCE.json records every selected native file
hash; installation preserves those source and asset bytes without applying patches.
No upstream implementation or asset bytes are vendored in this repository.

The installer excludes provider/agent/runner code, website material, and histories.
It installs the native game payloads, required utility modules, frozen level
configs, and their original environment configs. Runtime verifies every required
file before copying the selected payload to a private episode working directory.
VMAGE_ROOT is a trusted simulator deployment setting; the default is /opt/vmage.
An instance cannot choose a Python module or source path.

Exactly one game and one episode may be constructed in a process. Initialization
calls the original init_run including step("None", 0), native capture, history and
ledger append. native_step_calls includes that initialization. The separate
native_frames_advanced counts later native updates only, excluding initialization
and the Race frame-limit precheck that returns without an update. native_frame_count
is exactly len(game_frames); the native first-action/passive-terminal capture
asymmetry is retained and validated by metric rules. Screenshot files are pruned
after cache refresh, while the complete native path ledger/count is retained.

observe returns the latest original native capture PNG. A terminal passive update
has no new capture in PygameBase, so that PNG remains the preceding captured frame.
frame returns a copy of the cached full-resolution native surface after the final
update. Both methods are pure reads and never call render. The public recorder
samples decisions; it is not a complete native 30 FPS video.

The strict frozen Python, SDL and engine versions are declared independently in
each stdlib-only schema. requirements.txt also includes imageio-ffmpeg for the
common recorder. The research host resolves native Pong SysFont("Courier") to
/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf with SHA256
39c29931201f08dd89fdba4129c76288e6baeecf7c94fe4f6a757f2b50718b1b
(Ubuntu fonts-dejavu-core 2.37-2build1). Container font packages must be frozen;
a distro package name alone does not establish byte-identical pixel rendering.
Fingerprints omit resource objects and wall-clock timestamps. They bind explicit
native game state, Python/NumPy RNG state, decisions and counters, and are not
restorable checkpoints. Tempest retains upstream wall-clock explosion/death visuals.

Licensing remains unresolved for upstream modifications and third-party assets.
This integration does not infer redistribution rights from the Game Exam license.
