// Violates: fp-typescript 5 — throwing internally instead of errors as
// values.
// Expected: CAUGHT by no-throw-internal.
export const requireId = (payload: Record<string, string>): string => {
  const id = payload.id;
  if (id === undefined) {
    throw new Error("id is required");
  }
  return id;
};
