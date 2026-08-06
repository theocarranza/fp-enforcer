# Codex adapter

Codex requires the marketplace index at `.agents/plugins/marketplace.json` (the build emits that path; `.codex-plugin/marketplace.json` is also written for Open Plugins parity).

## Install (users)

One command for this repo:

```bash
curl -fsSL https://raw.githubusercontent.com/theocarranza/fp-enforcer/main/adapters/codex/install.sh \
  | bash -s -- --repo theocarranza/fp-enforcer --ref main
```

Forks: replace `theocarranza/fp-enforcer` with `OWNER/REPO`.

From a local clone:

```bash
./adapters/codex/install.sh
```

Copies a durable marketplace under `~/.agents/plugins/fp-enforcer-codex-marketplace`, then runs:

```bash
codex plugin marketplace add <durable-path>
codex plugin add fp-enforcer@fp-enforcer-local
```

Restart Codex or start a new thread, then invoke `/fp-enforcer:fp-validate`.

Flags: `--dry-run`, `--prefix DIR`. Uninstall: `adapters/<host>/uninstall.sh`. (copies marketplace only; prints CLI commands and skips registration).


## Uninstall



From a local clone: .

## Authoring / build

```bash
python3 adapters/codex/build_plugin.py
```

## Fallback

Load the repo root as an Open Plugins directory when the host supports `.plugin/plugin.json`.

## Note

Some Codex setups place agents outside the plugin tree. Keep Codex-specific agent files under `adapters/codex/agents/` and document any out-of-plugin install steps here as you add them.
