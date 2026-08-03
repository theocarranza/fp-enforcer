// Violates: fp-typescript 1 & 6 — mutation of bindings, arrays, and objects
// instead of patch objects and pure transformations.
// Expected: MISSED — no pattern exists.
export const appendTag = (tags: string[], tag: string): string[] => {
  tags.push(tag);
  tags.sort();
  return tags;
};

export const rename = (
  user: { name: string },
  name: string,
): { name: string } => {
  user.name = name;
  return user;
};
