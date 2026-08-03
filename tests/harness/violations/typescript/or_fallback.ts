// Violates: fp-typescript 3 — || for absence, which swallows valid falsy
// values (0, "", false).
// Expected: MISSED — no pattern exists.
export const retries = (config: { retries?: number }): number =>
  config.retries || 3;

export const displayName = (user: { name?: string }): string =>
  user.name || "anonymous";
