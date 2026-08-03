// Violates: fp-core branching 2 — else branches instead of expression
// lookups or pattern-matched returns.
// Expected: CAUGHT by no-else.
export const label = (status: string): string => {
  if (status === "ok") {
    return "healthy";
  } else if (status === "warn") {
    return "degraded";
  } else {
    return "down";
  }
};
