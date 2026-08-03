// Violates: fp-typescript 1 — var instead of const.
// Expected: CAUGHT by no-var.
export function buildKey(parts: string[]): string {
  var key = parts.join(":");
  return key;
}
