// Compliant: typed errors at the outermost edge are permitted
// (fp-typescript 5) and allowlisted by no-throw-internal.
// Expected: NO violations reported.
class HttpsError extends Error {
  constructor(
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

export const handler = (payload: Record<string, string>): string => {
  const id = payload.id ?? "";
  if (id === "") {
    throw new HttpsError("invalid-argument", "id is required");
  }
  return id;
};
