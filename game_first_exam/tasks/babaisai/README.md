# Baba Is AI minimal integration

Two frozen smoke tasks: env/goto_win and env/two_room-break_stop-make_win, seed 2117382936. Engine commit 40ae1b29dbc67f2ecea06cc161ed5ca51719e5e3 is vendored unchanged with MIT license and source hashes. Constructed with native defaults (100 steps); native actions, rewards and win/loss conditions are preserved.

Suite 1.0.0 uses native-rgb-v1: direct native rendering at the default 32 pixels per tile. No derived cells, object naming scheme, parsed rules or hidden layers. Old board-symbolic-rgb-v1/v2 results keep their original labels and images.

The adapter translates Gym done into termination/truncation and supplies native metrics to an isolated verifier. Common services provide request deduplication, evidence collection, fault classification and recording. Run `scripts/run_games.py --suite babaisai` with oracle, nop or tamper. The reference traces contain 6 and 25 native moves.

This is interactive engine integration, not the paper's static-image high-level-plan exact-match evaluation. That evaluator is a different task interface and is not added in this change. See [framework](../../../docs/game_framework.md).
