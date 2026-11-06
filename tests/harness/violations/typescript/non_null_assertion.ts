// Violates: fp-typescript seams 2 — a non-null assertion hides absence
// instead of naming the fallback.
// Expected: no-non-null-assertion.
type Entry = { readonly code: number };
const TABLE: ReadonlyMap<string, Entry> = new Map([["internal", { code: 500 }]]);
export const lookup = (key: string): Entry => TABLE.get(key) ?? TABLE.get("internal")!;
export const firstCode = (entries: ReadonlyArray<Entry>): number => entries[0]!.code;
