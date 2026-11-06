// Lookup tables — replace branching with data (plain TypeScript).
// Run: node fp_enforcer/rules/examples/typescript/lookup-tables.ts  (Node >= 22.6)
//
// Principle: when N keys map to N answers, the mapping is data, not control
// flow. One table is the single source of truth; the fallback is a named
// entry of that table, reached with `??` (never `||`, never `!`).

import assert from "node:assert/strict";

export interface StatusEntry {
  readonly httpCode: number;
  readonly message: string;
}

const INTERNAL: StatusEntry = { httpCode: 500, message: "Internal server error." };

const STATUS: ReadonlyMap<string, StatusEntry> = new Map([
  ["ok", { httpCode: 200, message: "Operation successful." }],
  ["created", { httpCode: 201, message: "Resource created successfully." }],
  ["cancelled", { httpCode: 499, message: "Operation cancelled." }],
  ["invalid-argument", { httpCode: 400, message: "Invalid argument provided." }],
  ["not-found", { httpCode: 404, message: "Resource not found." }],
  ["permission-denied", { httpCode: 403, message: "Permission denied." }],
  ["unauthenticated", { httpCode: 401, message: "User not authenticated." }],
  ["internal", INTERNAL],
]);

export const fetchStatusCode = (key: string): StatusEntry => STATUS.get(key) ?? INTERNAL;

assert.equal(fetchStatusCode("not-found").httpCode, 404);
assert.equal(fetchStatusCode("no-such-code"), INTERNAL);
