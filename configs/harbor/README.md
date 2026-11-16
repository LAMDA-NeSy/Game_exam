# Native Harbor run configurations

These are ordinary Harbor 0.23.0 JobConfig files, with no custom model runner or secret values.
From the repository's editable installation:

```bash
harbor run --game-suite minihack-balrog --list
harbor run --game-suite minihack --standard -a codex -m deepseek-flash
harbor run --game-suite minihack --standard -a claude-code -m <your-model-id>
harbor run --game-suite minihack-balrog -c configs/harbor/oracle.json \
  --plugin game_harbor:GameRecords --job-name minihack-oracle
harbor run --game-suite minihack --standard --family room -c configs/harbor/codex-deepseek.json \
  --plugin game_harbor:GameRecords --job-name minihack-deepseek
```

The primary interface is the same native `-a` / `-m` / `--ak` interface as upstream.
Only task selection changes. We do not maintain another agent/model compatibility list or
implement model calls. Any Harbor-native agent or import path is passed through; installation,
provider routing, credentials and actual model compatibility remain the selected agent's concern.
An omitted model uses its native default if available. None of this claims every combination has
been executed here. Existing tasks retain standard. The initial additional modes cover MiniHack Room privileged and
Crafter survival i01 realtime only; mode flags cannot create other missing task implementations.

The JSON profiles below remain optional reproducible examples. Direct `-a` / `-m` commands use
native defaults unless options are explicitly supplied; they do **not** silently load the Codex
profile's tool policy or version. For those settings, use the complete profile or supply all desired
`--ak` values. Switching agents must not carry Codex-only kwargs into a different implementation.

`--game-suite` uses the existing EFE selection entry point, with `--benchmark`, mode flags,
`-i`/`-x` task-name globs, `-p` directory scope and `-l` task count. `--family` filters suite
families. It never adds embodied tasks to a game suite. `--list` validates and lists without
building images or running a model. `--core`/`--all` select game-only sets and cannot
be combined with `--game-suite`. Existing native `-p`/`-c` commands still work.

Use **one** agent profile: `oracle.json` (reference solution), `nop.json` (no-op), or
`codex-deepseek.json` (paid model). All specify one attempt, one concurrent trial and no automatic
retries. The latter preserves the previously used `deepseek-flash` model and Codex CLI `0.167.1`.
`agents[].model_name` is the provider's model ID; `agents[].kwargs.version` is the **agent CLI**
version, not a model snapshot. `deepseek-flash` is an alias and does not pin the provider's weights.
Use a provider-supported immutable ID in a copied profile when available.

The Codex profile disables web search, apps, account connectors, plugins and image generation,
while retaining shell/Python execution and game client calls. These are agent tool settings,
not a replacement for task/container network isolation. The Harbor `GameRecords` job plugin is
independent of Codex plugins. Credentials and custom provider routing use existing Harbor/Codex
authentication; they are not stored here. A profile alone does not configure a new provider account.

Edit/copy the profile to change model or agent version. Harbor merges repeated `-c` using native
semantics: agent/task lists are **appended**, not replaced. Keep these profiles free of task/dataset
entries and do not layer two agent profiles. Adding `-a` replaces the entire profile agent,
including its kwargs/tool policy; `-m` alone is not a model override in this pinned Harbor version.
Avoid those flags with a profile unless deliberately replacing the complete agent configuration.
`--ak` explicitly overrides individual agent kwargs; changing `config` replaces that entire kwargs value.

`config.json` and `lock.json` in the Harbor job directory record the resolved configuration.
Staged tasks are retained under repository `jobs/prepared/` (even with a different `--jobs-dir`);
keep them for lock verification. `prepare_games.py` remains available for separate preparation.
The old `run_games.py` launcher delegates ordinary runs to `harbor run --game-suite` and accepts
`--mode`, arbitrary native `--agent`, `--model`, `--agent-version` and repeatable `--ak`.
Its legacy Codex callers still read the Codex profile; other agents get their own native defaults,
without Codex kwargs. Legacy overrides are materialized in a native config before launch.
Tamper testing alone still
prepares a separate fixture copy. No benchmark adapter, instruction or score changes are implied.

## Initial game modes

Choose a mode explicitly when a suite contains more than one:

```sh
harbor run --game-suite minihack --privileged -a oracle
harbor run --game-suite crafter --realtime -a oracle
```

MiniHack privileged currently contains Room only. Crafter realtime contains survival i01 only.
These are initial integration tasks; the other games and MiniHack tasks remain standard.
Optional GameRecords reports reject mixed-mode jobs so different observation/interaction conditions
are not averaged together. Harbor's own records remain unchanged.

For paid DeepSeek runs, choose exactly one native profile:

```sh
harbor run --game-suite minihack --privileged -c configs/harbor/codex-deepseek.json
harbor run --game-suite minihack --standard --family room -c configs/harbor/claude-deepseek.json
harbor run --game-suite crafter --realtime -c configs/harbor/codex-deepseek.json
```

The Codex DeepSeek profile uses `OPENAI_API_KEY` (the DeepSeek key) and an explicit native
Codex provider pointing at `https://api.deepseek.com`, with Responses over HTTP streaming.
WebSockets are disabled for this provider to avoid unsupported-handshake retries. This profile's
provider URL is explicit; `OPENAI_BASE_URL` alone does not override it. Copy/edit the provider
configuration when changing endpoints. No model gateway or custom agent is added.
Claude Code uses `ANTHROPIC_API_KEY` (the DeepSeek key) and
`ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic`.
Set these for the selected process/provider; do not overwrite credentials for a different account.
The Claude profile pins CLI 2.1.325, limits turns to 12, and sets a native $1 budget flag.
Client-reported cost can use a different pricing table from the actual provider; retain tokens and
estimate provider list-price cost separately. A successful DeepSeek call through Claude Code does
not validate Anthropic-hosted Claude models. GPT/Gemini examples also require their own credentials
and an agent/provider combination that supports the selected API.
