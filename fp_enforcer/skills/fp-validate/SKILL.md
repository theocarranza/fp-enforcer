---
name: fp-validate
description: Use when asked to lint, validate, or check code blocks, diffs, pull requests, or an entire codebase for functional-programming compliance.
license: MIT
---

# FP Validate

Run the fp-enforcer CLI to scan for heuristic pattern violations against the canonical rules in `.fp-enforcer/rules/`.

## Scope

**Specific paths or directories**

```bash
fp-enforcer validate path/to/file.dart lib/
```

**Git diff (added lines only)**

```bash
git diff | fp-enforcer validate --diff -
```

**Whole tree** — pass the project root or `.`:

```bash
fp-enforcer validate .
```

**Whole files, legacy code included**

```bash
fp-enforcer scan-legacy path/to/file.ts src/
```

This is the explicit way to scan code the hooks skip: it reports every finding in each whole file, not only in changed lines.

When installed in a target project, rules and pattern packs live under `<project>/.fp-enforcer/rules/`. Run commands from the project root so relative paths resolve correctly.

If the `fp-enforcer` executable is not on PATH, run the vendored copy instead: `PYTHONPATH=.fp-enforcer python3 -m fp_enforcer validate ...`.

## Hooks report only changed lines

The edit hook and the completion gate (Stop) scan each touched file as a whole, then report only the findings on lines added or changed relative to the diff base. Findings on untouched legacy lines are not reported; run `fp-enforcer scan-legacy` to see them.

- The diff base is `HEAD`, so uncommitted work is gated. To gate a whole branch, set `FP_ENFORCER_DIFF_BASE` to any git revision, for example `origin/main` or a merge-base SHA. The completion gate's list of changed files uses the same base.
- An untracked (new) file counts as entirely new: all its findings are reported.
- If git is unavailable, the file is outside a git repository, or the diff cannot be computed (for example a bad base), the edit hook scans the whole file. The completion gate falls back to the whole-file scan for a bad base; outside a git repository it has no change list and reports nothing.

## Reading the report

Each violation line follows this format:

```
path:line: [pattern-id] message (rule)
```

Example:

```
lib/use_case.dart:42: [no-else] no else branches: use switch expressions or fold (fp-core 8-9)
```

- **path:line** — file and line number to inspect.
- **pattern-id** — identifier from `rules/patterns/<language>.json`.
- **message** — human-readable violation summary.
- **rule** — canonical rule reference (e.g. `fp-core 8-9`, `fp-dartz 7`).

## Heuristic caveats

Pattern packs are line-scanners, not semantic analyzers. A flagged line deserves judgment before treating it as a real violation. Common false positives:

- `else` inside a string literal or comment
- `throw` in generated or third-party code excluded by suffix filters
- `var` in a doc comment or example block

Consult the cited rule file under `.fp-enforcer/rules/` when context is unclear.

## Success criteria

- **Exit code 0** with no output — the scanned scope is compliant.
- **Exit code 1** with one or more report lines — violations found; use `fp-repair` to fix them.
