---
name: fp-learn
description: Use when asked to assimilate or learn the FP libraries present in a project so enforcement and repair understand their operators and types.
---

# FP Learn

Detect functional-programming libraries in a project and generate agent-facing knowledge profiles for enforcement and repair.

## Run the learn CLI

```bash
fp-enforcer learn --dest /path/to/project
```

The tool inspects `pubspec.yaml` and `package.json` for known FP libraries:

- **Dart:** dartz, fpdart, rxdart
- **TypeScript:** fp-ts, effect, rxjs

Profiles are written to:

```
<project>/.fp-enforcer/knowledge/
```

Review each generated profile before relying on it in repair or code generation.

## Review generated profiles

Each profile summarizes:

- **Types** — core ADTs and their roles (e.g. `Either`, `Option`, `Task`, `IO`)
- **Operators** — key combinators (`flatMap`, `fold`, `mapLeft`, etc.)
- **Composition idioms** — canonical chains for common patterns
- **Do/Don't** — library-specific constraints aligned with the canonical rules

Use these profiles when interpreting validation reports or rewriting violating code.

## Unknown libraries

When a project uses an FP library the tool does not detect, author a profile manually under `.fp-enforcer/knowledge/<library>.md` with the same sections:

1. **Types**
2. **Operators**
3. **Composition idioms**
4. **Do/Don't**

Keep profiles concise and aligned with the rules in `.fp-enforcer/rules/`.

## Extending pattern packs

When a new library introduces constructs that should be banned or flagged, add entries to the appropriate pattern pack:

```
<project>/.fp-enforcer/rules/patterns/<language>.json
```

Each pattern entry requires:

```json
{"id": "unique-id", "regex": "...", "message": "...", "rule": "fp-* N"}
```

Re-run `validate` after adding patterns to confirm they match intended constructs and avoid excessive false positives.
