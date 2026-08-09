# Changelog

All notable changes to fp-enforcer are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.2] - 2026-08-09

### Fixed

- Plugin-level `hooks/hooks.json` now uses a valid no-op descriptor (removed unsupported top-level `version` and sample per-project hook commands that triggered schema warnings).

### Changed

- `scripts/validate.sh` enforces plugin hook schema (empty `hooks` object only) and runs in CI.
- Regression tests guard against schema drift in shipped plugin hooks.

## [0.3.1] - 2026-08-06

### Changed

- Adapted repository to the Open Plugins / agent-plugin-template shape (same pattern as agent-continuity):
  `.plugin/plugin.json`, root `VERSION` lockstep, `adapters/{cursor,claude,codex}/` with
  dedicated `install.sh` / `uninstall.sh`, and `scripts/validate.sh` + `scripts/build_all.sh`.
- Flattened portable skills to root `skills/` (mirrored under `fp_enforcer/skills/` for wheels).
- Extended adapter packaging to ship all five skills, the `fp_enforcer` Python package, hooks, assets, and Cursor rules.

### Added

- Curl one-liner install/uninstall UX per host; plain install upgrades in place.
- `.agents/plugins/marketplace.json` for Codex-accepted marketplace paths.

### Fixed

- PyPI wheel now includes `fp_enforcer.adapters`. Setuptools was listing only
  the top-level `fp_enforcer` package, so `wire` succeeded but the vendored
  hook runner failed with `ModuleNotFoundError: No module named
  'fp_enforcer.adapters'`.

## [0.3.0] - 2026-08-03

### Added

- PyPI packaging: `pyproject.toml` with the `fp-enforcer` console script and
  `rules/` + `skills/` shipped as package data. Install with
  `pipx install fp-enforcer` (or `uv tool install fp-enforcer`); update with
  `pipx upgrade fp-enforcer` + re-wire. No local checkout required.
- GitHub Actions: CI on Python 3.10/3.12 and a tag-triggered release workflow
  publishing to PyPI via trusted publishing.
- Marketplace adapters: Claude Code marketplace catalog
  (`.claude-plugin/marketplace.json`), Codex plugin manifests (`plugin.json`,
  `marketplace.json`), and Cursor plugin manifest
  (`.cursor-plugin/plugin.json`). Plugins deliver skills and rules; hooks are
  wired per-project by `fp-enforcer wire` to avoid double execution.

### Changed

- CLI: `install` renamed to `wire` and `uninstall` to `unwire`; the old names
  remain as aliases.
- Skill: `fp-bootstrap` renamed to `fp-wire`; all skills now invoke the
  `fp-enforcer` console script.
- `rules/` and `skills/` moved inside the `fp_enforcer` package so wheels are
  self-contained; the vendored `.fp-enforcer/` project layout is unchanged.

## [0.2.1] - 2026-08-03

### Fixed

- Pack `rule` cross-references now use section-qualified numbering aligned with
  per-section rule lists (`fp-core branching 4`, `fp-dartz task 1`, …); completed
  the `fp-dartz` renumber and repaired `fp-typescript` list numbering.
- Regenerated `.cursor/rules/*.mdc` from the canonical rule sources so Cursor
  sees the same section numbering the packs cite.
- Dart SDK detection accepts spaced range forms (`sdk: ">= 3.0.0 <4.0.0"`).

### Added

- Assimilate prunes stale packs from `.fp-enforcer/rules/patterns/learned/` when
  their library/feature is no longer detected.
- CLI exit-code tests for `validate`, `learn`, and `assimilate`.
- Pack rule-reference resolver test (`tests/test_rule_refs.py`) so numbering
  drift fails the suite.

## [0.2.0] - 2026-08-03

### Added

- Multi-pack scanning: `packs_for` matches every applicable pack per file
  with deduped violations, and `load_packs` picks up a `learned/`
  subdirectory of activated packs.
- `python3 -m fp_enforcer assimilate`: detects FP libraries and language
  features (Dart SDK constraint), activates curated packs from
  `rules/patterns/libraries/` into the project's
  `.fp-enforcer/rules/patterns/learned/`, fail-closed on each pack's
  embedded self-test.
- Curated packs for `rxjs` (no-manual-subscribe, no-unbounded-replay-ts)
  and `dart3` (prefer-switch-expression).
- `fp-assimilate` skill with the activation workflow and the manual
  pack-authoring path for uncurated libraries.
- New Dart patterns: no-for-loop, no-throw-domain, no-reassignment,
  no-mutable-field, no-late, no-collection-mutation, no-stateful-widget,
  no-manual-listen, no-unbounded-replay — `fp-flutter` and `fp-rxdart` rules
  now have pattern coverage.
- New TypeScript patterns: no-or-fallback, no-for-loop,
  no-collection-mutation, no-field-write.
- Inline suppression: `// fp-allow: <pattern-id>` on the violating line or
  the comment line directly above waives named patterns, keeping justified
  exceptions explicit and auditable.
- Comment-aware scanning: line and block comments are stripped before
  pattern matching (block state tracked across lines), and string literals
  are respected so a `//` inside a string no longer truncates the line.
- Test harness (`tests/harness/`): violation fixtures per rule area with
  hermetic library stubs (`tests/harness/stubs/`, `.g.dart`-excluded),
  suppression fixtures, and clean fixtures (rule-compliant code that must
  produce zero violations); regression-check with
  `python3 -m fp_enforcer validate tests/harness`.
- Harness regression tests (`tests/test_harness.py`): pin exact pattern ids
  per violation fixture (recall) and zero-violation guarantees for clean,
  suppression, and stub fixtures (precision).

### Changed

- no-var/no-let widened from line-anchored to word-boundary matching,
  catching `for (var x in ...)` / `for (let i ...)` forms.
- no-throw-internal/no-throw-domain allowlist crash-only exception types
  (`HttpsError`, `UnimplementedError`, `UnsupportedError`, `AssertionError`)
  that the rules reserve for the platform/edge.
- no-field-write excludes `this.` receivers, so idiomatic constructor
  initialization no longer trips it.
- no-reassignment and no-field-write exclude the `=>` arrow, so switch
  expression arms (e.g. `_ => 'bronze'`) no longer trip them.
- Unit test suite grew to 70 tests.

## [0.1.0] - 2026-08-02

### Added

- Canonical functional programming rule set (`rules/`), vendor-neutral markdown
  with a `manifest.json` index: `fp-core`, `fp-dart-style`, `fp-dartz`,
  `fp-rxdart`, `fp-flutter`, `fp-typescript`.
- Machine-readable pattern packs (`rules/patterns/`) for Dart (fold-not-unwrap,
  no-else, no-var, no-try-catch, no-tuple-return, no-async-void) and
  TypeScript (no-let, no-var, no-else, no-throw-internal).
- Violation scanner (`fp_enforcer.validate`): files, directory trees, and
  added-lines-only unified-diff scanning with rule-linked reports.
- Hook runtime (`fp_enforcer.hook_runtime`) with post-edit guard and
  git-aware completion gate (optional `dart analyze` integration).
- Vendor adapters for Cursor, Claude, Codex, and Antigravity payloads and
  response formats.
- Installer (`fp_enforcer.install`): vendors the runtime into the target
  project's `.fp-enforcer/`, renders per-client rules and hook wiring, merges
  `hooks.json`/`settings.json` non-destructively and idempotently, and records
  an install manifest. Uninstall reverses only what was installed, prunes
  empty directories, and leaves foreign configuration intact.
- Library profiler (`fp_enforcer.learn`): detects FP libraries from
  `pubspec.yaml`/`package.json` (dartz, fpdart, rxdart, fp-ts, effect, rxjs)
  and writes agent-facing knowledge profiles.
- Agent skills per the agentskills.io specification: `fp-validate`,
  `fp-repair`, `fp-learn`, `fp-bootstrap`.
- Claude Code plugin manifest (`.claude-plugin/plugin.json`) and Cursor hook
  template (`hooks/hooks.json`).
- Unit test suite (31 tests, stdlib `unittest`).
- Self-hosted enforcement: the repository's own `.cursor/` harness is
  generated by its own installer.

[Unreleased]: https://github.com/theocarranza/fp-enforcer/compare/v0.3.2...HEAD
[0.3.2]: https://github.com/theocarranza/fp-enforcer/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/theocarranza/fp-enforcer/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/theocarranza/fp-enforcer/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/theocarranza/fp-enforcer/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/theocarranza/fp-enforcer/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/theocarranza/fp-enforcer/releases/tag/v0.1.0
