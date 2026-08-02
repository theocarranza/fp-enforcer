
# TypeScript: Functional Seams

The core paradigm rule applies in full. TypeScript specifics:

1. `readonly` on every interface field; `const` only — no `let`, no mutation.
2. Replace branching lookups with data: a `Map` (or frozen record) plus nullish coalescing for the fallback, keeping a single source of truth.

```typescript
export const fetchStatusCode = (key: string): StatusEntry =>
  STATUS_MAP.get(key) ?? STATUS_MAP.get("internal")!;
```

3. Prefer `??` over `||` for absence — `||` swallows valid falsy values.
4. Brand primitive types that carry domain meaning; refine with type guards and named predicates instead of inline boolean soup.
5. Errors as values internally; `null` is acceptable at internal seams, typed errors (`HttpsError` etc.) only at the outermost edge.
6. Partial updates travel as patch objects, not mutations.
7. Fold aggregations with monoids: a `concat` plus an identity `empty` replaces accumulator loops (`{ concat: (x, y) => x + y, empty: 0 }`).
8. Arrow-function expression bodies; pipelines of `map`/`filter`/`reduce` over loops; small named helpers over comments.
