---
name: fp-assimilate
description: Use when asked to assimilate FP libraries or language features of a project into enforcement — activates curated pattern packs so validation and hooks understand library-specific anti-patterns.
license: MIT
---

# FP Assimilate

Turn detected FP libraries and language features into active enforcement.
Assimilation has two channels: knowledge profiles (advisory, via `fp-learn`)
and pattern packs (enforced, via this skill).

## Run the pipeline

```bash
fp-enforcer learn --dest /path/to/project
fp-enforcer assimilate --dest /path/to/project
```

`learn` writes agent-facing profiles to `.fp-enforcer/knowledge/`.
`assimilate` detects FP libraries (`pubspec.yaml`, `package.json`) and
language features (SDK constraints), then activates curated packs from the
canonical `rules/patterns/libraries/` into:

```
<project>/.fp-enforcer/rules/patterns/learned/
```

Activation is fail-closed: every curated pack carries a `self_test` payload
and is only installed when its violation strings produce violations and its
clean strings produce none. Gate failures are printed to stderr and exit 1.

## Verify activation

```bash
fp-enforcer validate --patterns-dir <project>/.fp-enforcer/rules/patterns <project>/lib
```

Confirm activated packs fire on real code without flooding false positives.
If a pack is too noisy, remove it from `learned/` or suppress individual
sites with `// fp-allow: <pattern-id>`.

## Libraries without a curated pack

When detection reports a library with no matching pack, author one at
`rules/patterns/libraries/<library>.json` in the fp-enforcer source repo:

1. Copy an existing pack as the template — keep `language`, `suffixes`,
   `exclude_suffixes` consistent with the language.
2. Write only regex-enforceable anti-patterns; idioms and opportunities
   belong in the knowledge profile (see `fp-learn`), not the scanner.
3. Add a `self_test` with at least two `violations` strings (each must be
   flagged) and two `clean` strings (each must not be flagged, suppression
   directives allowed).
4. Run the gate locally:

```bash
python3 -m unittest tests.test_assimilate.CuratedPackTests -v
```

5. Re-run `assimilate` in the target project and verify with `validate`.

Watch suppression density after activation: repeated `fp-allow` directives
for the same pattern id across a project mean the pattern is wrong, not the
code — fix or retract the pack.
