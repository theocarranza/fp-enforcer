---
name: fp-bootstrap
description: Use when asked to install, wire, update, or uninstall fp-enforcer into a coding project for Cursor, Claude, Codex, or Antigravity.
---

# FP Bootstrap

Install or remove fp-enforcer integration in a target project. All runtime artifacts live inside the target project under `.fp-enforcer/`.

## Install

```bash
python3 -m fp_enforcer install --client {cursor|claude|codex|antigravity|all} --dest /path/to/project
```

Use `--client all` to wire every supported agent at once.

## Uninstall

```bash
python3 -m fp_enforcer uninstall --dest /path/to/project
```

Removes client-specific wiring and the `.fp-enforcer/` directory according to the install manifest.

## What gets rendered per client

| Client | Artifacts |
|--------|-----------|
| **cursor** | `.cursor/rules/*.mdc` (from canonical rules) + `.cursor/hooks.json` entries |
| **claude** | `.claude/skills/` copies + `.claude/settings.json` hook entries |
| **codex** | `.codex/hooks.json` entries |
| **antigravity** | `.agent/rules/*.md` copies |

Rules source of truth after install: `<project>/.fp-enforcer/rules/`.

Hook runner: `<project>/.fp-enforcer/run_hook.py`.

## Merge behavior

Install and uninstall are **non-destructive** and **idempotent**:

- Existing client config files are merged, not replaced wholesale.
- Re-running `install` updates rules and hook entries without duplicating them.
- State is tracked in `<project>/.fp-enforcer/install_manifest.json`.

## Update

To refresh rules or hook wiring after upgrading fp-enforcer, re-run install:

```bash
python3 -m fp_enforcer install --client all --dest /path/to/project
```

Everything stays inside the target project; no global agent configuration is modified.
