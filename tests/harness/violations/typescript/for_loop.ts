// Violates: fp-typescript 8 / fp-core data 4 — imperative loops instead of
// map/filter/reduce pipelines.
// Expected: MISSED — no pattern exists.
export const evens = (values: readonly number[]): number[] => {
  const out: number[] = [];
  for (let i = 0; i < values.length; i++) {
    if (values[i] % 2 === 0) {
      out.push(values[i]);
    }
  }
  return out;
};
