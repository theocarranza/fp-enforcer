// Violates: fp-typescript 1 — let instead of const.
// Expected: CAUGHT by no-let.
export const accumulate = (values: readonly number[]): number => {
  let sum = 0;
  for (const value of values) {
    sum += value;
  }
  return sum;
};
