# V-MAGE Race adapter (internal research)

This thin adapter runs the unchanged native game at commit `95d5d4a445bb0b75cce765c93107d87f84613e4d`.
`../common/SOURCE.json` binds externally fetched source and asset bytes.
Upstream and third-party licensing remain unresolved; do not publish the
native runtime payload or images without resolving those rights.

The one-process, one-episode lifecycle calls native `init_run()` exactly once,
including `step("None", 0)`. A decision performs 3 native
frames at literal dt 0.033 with 30 FPS pacing. Later frames repeat the selected action.
Native first-action and passive-terminal capture asymmetry is preserved.
The native capture-ledger limit varies by level. Each frozen instance declares its limit.
A native limit truncates the episode. Native death or victory terminates it.

Observations only return the cached PNG at 480×360 using
native pygame scaling. Queries never render or advance RNG. Native full-size RGB
is cached separately for decision-frame video. Screenshots are pruned after capture
while the native capture ledger is retained. Fingerprints bind explicit game state,
RNG and counters for auditing.

The primary metric is native_score, and transition reward is its difference.
Success is the native Race trophy win.
Illegal public actions are rejected without native advancement; the upstream
three-invalid-actions random fallback is intentionally not part of this protocol.
The original naive-agent prompt, parser and three-image history are not reproduced.
