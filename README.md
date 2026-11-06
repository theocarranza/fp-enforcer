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

fp-enforcer wire --client all --dest /path/to/project
# or one host: --client {cursor|claude|codex|antigravity}
fp-enforcer assimilate --dest /path/to/project   # activate curated library packs
```

## What gets enforced

**Rules** (`fp_enforcer/rules/*.md`, listed in `manifest.json`) are loaded into each agent's context:

| Host | Where the rules land |
| --- | --- |
| Cursor | `.cursor/rules/*.mdc` — core always, language rules by glob |
| Claude Code | `.claude/rules/*.md` — core always, language rules scoped with `paths:` |
| Codex | managed `<!-- fp-enforcer:begin/end -->` block in `AGENTS.md` (your content is preserved; `unwire` strips only the block) |
| Antigravity | `.agent/rules/*.md` |

`fp-core` is the language-agnostic mandate: purity and effects, errors as values, branching,
immutable data, and **Algebra** — every aggregation is a lawful monoid (associativity, identity,
derived record monoids, explicit first/last/applicative semantics for absence). `fp-typescript`
gives the TypeScript shape in plain TypeScript, no library required: seams, monoids, effects as
injected capabilities (one program, a production `Task` interpreter and a pure `State` test
interpreter), recursion instead of loops, and parse-don't-validate.

**References** ship with the rules and are vendored to `<project>/.fp-enforcer/rules/`:

- `examples/typescript/` — runnable, strictly typed, library-free (`monoids.ts`,
  `effects-as-capabilities.ts`, `lookup-tables.ts`; run with `node <file>`, Node ≥ 22.6).
- `libraries/<library>/` — the same programs written against a specific library (currently `fp-ts`).

**Hooks** scan every edit and gate completion (Stop) with the pattern packs in
`rules/patterns/`. TypeScript checks include `no-let`, `no-else`, `no-or-fallback`,
`no-for-loop`, `no-non-null-assertion`, `no-ambient-effect` (`Math.random`, `Date.now`,
`console.*`, `process.*` outside edge interpreters) and `no-seedless-reduce`. `assimilate`
adds curated library packs (`dart3`, `rxjs`, `fp-ts`). Justified edge cases are waived per
line with `// fp-allow: <pattern-id> — <reason>`.

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
fp_enforcer/rules/           Canonical rules, manifest.json, patterns/, examples/, libraries/
adapters/{cursor,claude,codex}/
scripts/validate.sh
scripts/build_all.sh
hooks/hooks.json             Valid no-op plugin hook descriptor
```

## License

MIT
