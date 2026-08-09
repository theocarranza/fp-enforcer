# FP Enforcer

Functional programming enforcement for AI coding harnesses: portable Agent Skills, curated pattern packs, a stdlib-only Python CLI, and per-project hooks for Cursor, Claude Code, Codex, and Antigravity.

Vendor-neutral **Open Plugins** root + **Agent Skills**. Host adapters build installable marketplaces; the Python package on PyPI remains the runtime used by `fp-enforcer wire`.

## Install (plugins)

One curl one-liner per host. Plain install **upgrades in place** (replaces any prior managed install). Uninstall is a **separate** script — there is no `--uninstall` on install.

Replace `REF` with `master` (or a tag) as needed.

### Claude Code

Install:

```bash
curl -fsSL https://raw.githubusercontent.com/theocarranza/fp-enforcer/master/adapters/claude/install.sh \
  | bash -s -- --repo theocarranza/fp-enforcer --ref master
```

Then:

```text
/plugin install fp-enforcer@fp-enforcer-local
```

Uninstall:

```bash
curl -fsSL https://raw.githubusercontent.com/theocarranza/fp-enforcer/master/adapters/claude/uninstall.sh \
  | bash -s -- --repo theocarranza/fp-enforcer --ref master
```

### Cursor

Install (curl → `~/.cursor/plugins/local`):

```bash
curl -fsSL https://raw.githubusercontent.com/theocarranza/fp-enforcer/master/adapters/cursor/install.sh \
  | bash -s -- --repo theocarranza/fp-enforcer --ref master
```

Uninstall:

```bash
curl -fsSL https://raw.githubusercontent.com/theocarranza/fp-enforcer/master/adapters/cursor/uninstall.sh \
  | bash -s -- --repo theocarranza/fp-enforcer --ref master
```

### Codex

Install:

```bash
curl -fsSL https://raw.githubusercontent.com/theocarranza/fp-enforcer/master/adapters/codex/install.sh \
  | bash -s -- --repo theocarranza/fp-enforcer --ref master
```

Codex marketplace manifests use `.agents/plugins/marketplace.json` (and mirrored accepted paths).

Uninstall:

```bash
curl -fsSL https://raw.githubusercontent.com/theocarranza/fp-enforcer/master/adapters/codex/uninstall.sh \
  | bash -s -- --repo theocarranza/fp-enforcer --ref master
```

From a clone: `./adapters/<host>/install.sh` or `./adapters/<host>/uninstall.sh`. Dry-run: add `--dry-run`.

## Runtime (PyPI)

Per-project wiring still uses the CLI:

```bash
pipx install fp-enforcer
# or: uv tool install fp-enforcer

fp-enforcer wire --dest /path/to/project --clients cursor,claude,codex,antigravity
```

Skills:

| Skill | Purpose |
| --- | --- |
| `fp-validate` | Scan paths/diffs for FP violations |
| `fp-repair` | Fix violations from a report |
| `fp-learn` | Detect FP libraries; write knowledge profiles |
| `fp-assimilate` | Activate curated pattern packs |
| `fp-wire` | Install runtime + wire per-project hooks/rules |

## Authoring / build

```bash
./scripts/validate.sh
./scripts/build_all.sh
```

Version lockstep is enforced across `VERSION`, `.plugin/plugin.json`, host manifests, adapter templates, and `pyproject.toml`. Do not hand-edit `dist/`.

Canonical skills live under `skills/<name>/SKILL.md` (portable frontmatter only: `name`, `description`, `license`). The same files are mirrored under `fp_enforcer/skills/` for wheel package data. Host overlays live in `adapters/<host>/skill-overlay.md`.

## Layout

```text
.plugin/plugin.json          Open Plugins manifest
skills/                      Portable Agent Skills
fp_enforcer/                 Python package (CLI, rules, adapters, mirrored skills)
adapters/{cursor,claude,codex}/
scripts/validate.sh
scripts/build_all.sh
hooks/hooks.json             Valid no-op plugin hook descriptor
```

## License

MIT
