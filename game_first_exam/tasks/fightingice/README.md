# FightingICE frozen tasks

Two standard smoke configurations use DareFightingICE 7.0, ZEN versus the pyftg
KickAI B-button example, switching the controlled player side. Native interface,
observation permissions, scoring, packaging and deviations are documented in
[the benchmark README](../../benchmarks/fightingice/README.md).

Run `harbor run --game-suite fightingice --standard --list` to validate the suite.
Run with `-c configs/harbor/oracle.json` for the reference controller, or with
`-c configs/harbor/nop.json` for a valid unfinished-match failure. Neither calls
a model. A complete no-key match is a separate native regression, not the nop
agent (which exits without playing).
