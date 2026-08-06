# Claude Code adapter

## Install (users)

One command for this repo:

```bash
curl -fsSL https://raw.githubusercontent.com/theocarranza/fp-enforcer/main/adapters/claude/install.sh \
  | bash -s -- --repo theocarranza/fp-enforcer --ref main
```

Forks: replace `theocarranza/fp-enforcer` with `OWNER/REPO`.

From a local clone:

```bash
./adapters/claude/install.sh
```

Copies a durable marketplace under `~/.agents/plugins/fp-enforcer-claude-marketplace`, then runs:

```text
claude plugin marketplace add <durable-path>
claude plugin install fp-enforcer@fp-enforcer-local
```

Equivalent in a Claude session:

```text
/plugin marketplace add <durable-path>
/plugin install fp-enforcer@fp-enforcer-local
```

Restart Claude Code if needed, then invoke `/fp-enforcer:fp-validate`.

Flags: `--dry-run`, `--prefix DIR`. Uninstall: `adapters/<host>/uninstall.sh`. (copies marketplace only; prints the `/plugin` commands and skips CLI registration).


## Uninstall



From a local clone: .

## Authoring / build

```bash
python3 adapters/claude/build_plugin.py
claude --plugin-dir dist/claude-marketplace/plugins/fp-enforcer
```

## Fallback

`claude --plugin-dir ./` against the repo root (vendor-neutral `.plugin/`).

## Unsupported

Skill-only install (dropping the plugin wrapper) is not equivalent when you rely on agents, hooks, or MCP entries.
