// Justified suppression: typed errors are permitted at the outermost edge
// (fp-typescript 5), but the tripwire cannot see edge context.
// Expected: NO violations reported.
export const handler = (payload: Record<string, string>): string => {
  const id = payload.id;
  if (id === undefined) {
    // fp-allow: no-throw-internal — outermost edge, fp-typescript 5
    throw new Error("id is required");
  }
  return id;
};
