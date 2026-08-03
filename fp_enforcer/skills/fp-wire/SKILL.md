---
name: fp-wire
description: Use when asked to install, wire, update, or remove fp-enforcer in a coding project for Cursor, Claude, Codex, or Antigravity.
---

# FP Wire

Wire a project to fp-enforcer: install the runtime from PyPI, then render rules, skills, and hooks into the target project. All per-project artifacts live under `.fp-enforcer/`.

## Install the runtime (once per machine)

```bash
pipx install fp-enforcer
# or: uv tool install fp-enforcer
```

If neither is available: `python3 -m pip install --user fp-enforcer`.

## Wire a project

```bash
fp-enforcer wire --client {cursor|claude|codex|antigravity|all} --dest /path/to/project
```

Use `--client all` to wire every supported agent at once.

## Unwire

```bash
fp-enforcer unwire --dest /path/to/project
```

Removes client-specific wiring and the `.fp-enforcer/` directory according to the install manifest.

## What gets rendered per client

| Client | Artifacts |
|--------|-----------|
| **cursor** | `.cursor/rules/*.mdc` (from canonical rules) + `.cursor/hooks.json` entries |
| **claude** | `.claude/skills/` copies + `.claude/settings.json` hook entries |
| **codex** | `.codex/hooks.json` entries |
| **antigravity** | `.agent/rules/*.md` copies |

Rules source of truth after wiring: `<project>/.fp-enforcer/rules/`.

Hook runner: `<project>/.fp-enforcer/run_hook.py` (self-contained; runs against the vendored copy, no global install needed at hook time).

## Merge behavior

Wire and unwire are **non-destructive** and **idempotent**:

- Existing client config files are merged, not replaced wholesale.
- Re-running `wire` updates rules and hook entries without duplicating them.
- State is tracked in `<project>/.fp-enforcer/install_manifest.json`.

## Update

Updates are a two-step remote refresh:

```bash
pipx upgrade fp-enforcer
fp-enforcer wire --client all --dest /path/to/project
```

Everything stays inside the target project; no global agent configuration is modified.
