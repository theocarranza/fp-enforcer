# Cursor adapter

## Install (users)

One command for this repo:

```bash
curl -fsSL https://raw.githubusercontent.com/theocarranza/fp-enforcer/main/adapters/cursor/install.sh \
  | bash -s -- --repo theocarranza/fp-enforcer --ref main
```

Forks: replace `theocarranza/fp-enforcer` with `OWNER/REPO`.

From a local clone:

```bash
./adapters/cursor/install.sh
```

Installs to `~/.cursor/plugins/local/fp-enforcer`. Restart Cursor or run **Developer: Reload Window**, then invoke `/fp-enforcer:fp-validate`.

Flags: `--dry-run`, `--prefix DIR`. Uninstall: `adapters/<host>/uninstall.sh`. (smoke tests; skips real Cursor home).


## Uninstall



From a local clone: .

## Authoring / build

```bash
python3 adapters/cursor/build_plugin.py
```

## Fallback

Load the repo root directly if the host accepts `--plugin-dir` / local plugin paths (Open Plugins layout).

## Unsupported as a substitute for the plugin

Copying only `skills/*/` without the plugin manifest drops commands, agents, rules, hooks, and MCP config. Use the full plugin or marketplace build when those matter.
