// Violates: fp-typescript monoids 3 / fp-core algebra 5 — folding without the
// identity throws on an empty array.
// Expected: no-seedless-reduce.
type Monoid<A> = { readonly concat: (x: A, y: A) => A; readonly empty: A };
export const total = (xs: ReadonlyArray<number>): number => xs.reduce((acc, x) => acc + x);
export const combineAll = <A>(M: Monoid<A>, xs: ReadonlyArray<A>): A => xs.reduce(M.concat);
