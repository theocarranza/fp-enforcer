// Compliant: map/filter/reduce pipelines and immutable array transforms
// (fp-typescript 1, 6 & 8). Expected: NO violations reported.
export const evens = (values: readonly number[]): number[] =>
  values.filter((value) => value % 2 === 0);

export const total = (values: readonly number[]): number =>
  values.reduce((sum, value) => sum + value, 0);

export const sortedCopy = (values: readonly number[]): number[] =>
  values.toSorted((a, b) => a - b);
