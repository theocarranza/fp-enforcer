// Compliant: branching lookup replaced with data — Map plus ?? fallback
// (fp-typescript 2-3). Expected: NO violations reported.
const STATUS_MAP: ReadonlyMap<string, string> = new Map([
  ["ok", "healthy"],
  ["warn", "degraded"],
]);

export const fetchStatus = (key: string): string =>
  STATUS_MAP.get(key) ?? "down";
