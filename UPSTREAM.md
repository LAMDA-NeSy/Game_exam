# Source and distribution boundary

Game Exam derives from [mll-lab-nu/embodied-first-exam](https://github.com/mll-lab-nu/embodied-first-exam), under its MIT license. The original copyright and permission notice remain in `LICENSE`.

The game work was prepared from a local derivative whose recorded HEAD was `30775e1a4b805bc47c1bd9f75253d88f7b2bb8af`, with subsequent local game changes. That identifier describes the local development baseline, not an assertion that the upstream repository contains this commit. This repository starts with a separate, game-only publication history.

Retained and adapted shared components include Harbor task selection, normalization, content-derived timestamps, files-only image packaging, resource monitoring, evidence collection/classification and service connection readiness. `shared/connection/service_connection.py` was moved from `embodied_first_exam/connection/` without changing its bytes. The frozen connection image payload therefore retains its existing digest.

The distribution excludes robot task trees, robot adapters/services/images/assets, RoboTwin submodules, upstream paper/site assets, website frontend/command-builder source, local evaluation records, credentials and the legacy MiniGrid i00 prototype. Shared runtime infrastructure remains because games depend on it. Historical task IDs and OCI image references remain as compatibility identifiers; this is not a mirror of upstream's full embodied benchmark.

Native environments are MiniGrid, Crafter, TextWorld/Jericho, Baba Is AI and MiniHack/NLE. Pinned dependencies and source provenance live under `game_first_exam/benchmarks/`, task README files and Docker recipes. Preserve included third-party license notices and inspect the upstream terms before redistributing additional assets. Package/source downloads are not bundled or relicensed merely because the integration code is MIT.

The website is maintained in a separate private repository. This public repository includes no site frontend, deployment configuration, private website history or personal experiment logs.
