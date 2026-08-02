---
name: fp-validate
description: Use when asked to lint, validate, or check code blocks, diffs, pull requests, or an entire codebase for functional-programming compliance.
---

# FP Validate

Run the fp-enforcer CLI to scan for heuristic pattern violations against the canonical rules in `.fp-enforcer/rules/`.

## Scope

**Specific paths or directories**

```bash
python3 -m fp_enforcer validate path/to/file.dart lib/
```

**Git diff (added lines only)**

```bash
git diff | python3 -m fp_enforcer validate --diff -
```

**Whole tree** — pass the project root or `.`:

```bash
python3 -m fp_enforcer validate .
```

When installed in a target project, rules and pattern packs live under `<project>/.fp-enforcer/rules/`. Run commands from the project root so relative paths resolve correctly.

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
