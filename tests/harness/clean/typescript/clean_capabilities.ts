// Compliant: effects arrive as capabilities; folds start from the identity;
// absence falls back to a named entry; non-null-looking text is not flagged.
// Expected: NO violations reported.
type Monoid<A> = { readonly concat: (x: A, y: A) => A; readonly empty: A };
interface Clock { readonly now: () => number }
interface Random { readonly nextInt: (upper: number) => number }
type Entry = { readonly code: number };
const INTERNAL: Entry = { code: 500 };
const TABLE: ReadonlyMap<string, Entry> = new Map([["internal", INTERNAL]]);
export const lookup = (key: string): Entry => TABLE.get(key) ?? INTERNAL;
export const roll = (random: Random): number => random.nextInt(6);
export const elapsed = (clock: Clock, start: number): number => clock.now() - start;
export const concatAll = <A>(M: Monoid<A>) => (xs: ReadonlyArray<A>): A => xs.reduce(M.concat, M.empty);
export const total = (xs: ReadonlyArray<number>): number => xs.reduce((acc, x) => acc + x, 0);
export const differs = (a: number, b: number): boolean => a !== b && !Number.isNaN(a);
export const cheer = (name: string): string => `Well done, ${name}!`;
