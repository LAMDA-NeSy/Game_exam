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
