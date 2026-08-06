---
name: fp-repair
description: Use when a validation report or hook feedback lists functional-programming violations that need to be fixed in source code.
license: MIT
---

# FP Repair

The fp-enforcer tool reports violations but never mutates code. The agent reads the report, applies fixes, and re-validates until clean.

## Procedure

### 1. Get a fresh report

Run validation before and after every repair pass:

```bash
fp-enforcer validate <paths...>
```

For hook-triggered feedback, re-run on the files that were edited.

### 2. Group and fix bottom-up

Group violations by file. Within each file, fix from the **bottom line upward** so earlier line numbers remain valid as you edit.

### 3. Canonical fixes

| Pattern | Fix |
|---------|-----|
| `else` / `else if` | Replace with `switch` expression or `.fold()` on the discriminant |
| `isLeft()` / `isRight()` / `isSome()` / `isNone()` | Replace with `.fold((left) => ..., (right) => ...)` |
| `var` (Dart) | Change to `final` or `const` |
| `let` / `var` (TypeScript) | Change to `const`; refactor mutations into new bindings |
| `try { ... } catch` in business logic | Wrap in `Task(() => call()).attempt().mapLeft(...).mapRight(...)` chain; `run()` only at boundary |
| `TupleN` return type | Replace with a named record or dedicated immutable class |
| `async void` | Change return type to `Future<void>`; ensure callers `await` |
| `throw` (TypeScript, internal) | Return a typed error value (`Result`, `Either`, or domain error ADT) |

### 4. Consult canonical rules

Before rewriting non-trivial logic, read the matching rule file:

- `.fp-enforcer/rules/fp-core.md` — branching, purity, immutability
- `.fp-enforcer/rules/fp-dart-style.md` — Dart style and asynchrony
- `.fp-enforcer/rules/fp-dartz.md` — Either, Option, Task chains
- `.fp-enforcer/rules/fp-typescript.md` — TypeScript seams and error handling

Match the idioms already used in the surrounding module.

### 5. Re-validate until clean

```bash
fp-enforcer validate <paths...>
```

Repeat until exit code 0 with no output. Do not claim completion without a clean validation run on every file you changed.
