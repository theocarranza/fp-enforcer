// Monoids — lawful aggregation in plain TypeScript (no library).
// Run: node fp_enforcer/rules/examples/typescript/monoids.ts  (Node >= 22.6)
//
// Principle: every aggregation is a monoid. Name the combining operation
// (`concat`) and its identity (`empty`), prove the laws, derive bigger
// monoids from smaller ones, and fold collections from `empty`.

import assert from "node:assert/strict";

// --- The abstraction --------------------------------------------------------

/** A Semigroup combines two values of the same type associatively. */
export interface Semigroup<A> {
  readonly concat: (x: A, y: A) => A;
}

/** A Monoid is a Semigroup with an identity element `empty`. */
export interface Monoid<A> extends Semigroup<A> {
  readonly empty: A;
}

// Laws (must hold for all x, y, z in A):
//   associativity:  concat(concat(x, y), z) = concat(x, concat(y, z))
//   left identity:  concat(empty, x) = x
//   right identity: concat(x, empty) = x
// If an identity exists it is unique.

// --- Primitive instances ----------------------------------------------------

/** Integer addition. Lawful only while results stay exact (|n| <= 2^53 - 1). */
export const sum: Monoid<number> = { concat: (x, y) => x + y, empty: 0 };

/** Integer multiplication. Same exactness caveat as `sum`. */
export const product: Monoid<number> = { concat: (x, y) => x * y, empty: 1 };

/** Exact arbitrary-precision addition — lawful for every bigint. */
export const bigSum: Monoid<bigint> = { concat: (x, y) => x + y, empty: 0n };

export const string: Monoid<string> = { concat: (x, y) => x + y, empty: "" };

/** Boolean conjunction (AND). */
export const all: Monoid<boolean> = { concat: (x, y) => x && y, empty: true };

/** Boolean disjunction (OR). */
export const any: Monoid<boolean> = { concat: (x, y) => x || y, empty: false };

/** Not every Semigroup is a Monoid: no `e` satisfies `x + " " + e === x`. */
export const spaced: Semigroup<string> = { concat: (x, y) => `${x} ${y}` };

// --- Folding ----------------------------------------------------------------

/** Fold a collection from `empty`: no seed argument, safe on `[]`. */
export const concatAll =
  <A>(M: Monoid<A>) =>
  (as: ReadonlyArray<A>): A =>
    as.reduce(M.concat, M.empty);

// --- Deriving monoids -------------------------------------------------------

/** A record is a monoid when every field is: combine field-wise. */
export const struct = <A extends Readonly<Record<string, unknown>>>(
  fields: { readonly [K in keyof A]: Monoid<A[K]> },
): Monoid<A> => {
  const entries = Object.entries(fields) as ReadonlyArray<
    readonly [keyof A & string, Monoid<unknown>]
  >;
  return {
    concat: (x, y) =>
      Object.fromEntries(entries.map(([k, M]) => [k, M.concat(x[k], y[k])])) as A,
    empty: Object.fromEntries(entries.map(([k, M]) => [k, M.empty])) as A,
  };
};

/** The dual monoid: same identity, arguments flipped. */
export const reverse = <A>(M: Monoid<A>): Monoid<A> => ({
  concat: (x, y) => M.concat(y, x),
  empty: M.empty,
});

// --- Absence: three lawful ways to combine optional values -------------------

export type Option<A> =
  | { readonly _tag: "None" }
  | { readonly _tag: "Some"; readonly value: A };

export const none: Option<never> = { _tag: "None" };
export const some = <A>(value: A): Option<A> => ({ _tag: "Some", value });

/** Leftmost `Some` wins. */
export const first = <A>(): Monoid<Option<A>> => ({
  concat: (x, y) => (x._tag === "Some" ? x : y),
  empty: none,
});

/** Rightmost `Some` wins — the dual of `first`; last-write-wins overrides. */
export const last = <A>(): Monoid<Option<A>> => reverse(first<A>());

/**
 * Both present → combine payloads; any `None` → `None`.
 * `empty` is `some(M.empty)`, not `none` (`none` absorbs, it is not an identity).
 */
export const applicative = <A>(M: Monoid<A>): Monoid<Option<A>> => ({
  concat: (x, y) =>
    x._tag === "Some" && y._tag === "Some" ? some(M.concat(x.value, y.value)) : none,
  empty: some(M.empty),
});

// --- Worked examples --------------------------------------------------------

type Point = { readonly x: number; readonly y: number };
type Vector = { readonly from: Point; readonly to: Point };

const pointMonoid = struct<Point>({ x: sum, y: sum });
const vectorMonoid = struct<Vector>({ from: pointMonoid, to: pointMonoid });

/** Settings overrides: one `last` monoid per field, user beats workspace. */
type Settings = {
  readonly fontFamily: Option<string>;
  readonly fontSize: Option<number>;
  readonly maxColumn: Option<number>;
};

const settingsMonoid = struct<Settings>({
  fontFamily: last<string>(),
  fontSize: last<number>(),
  maxColumn: last<number>(),
});

const workspace: Settings = { fontFamily: some("Courier"), fontSize: none, maxColumn: some(80) };
const user: Settings = { fontFamily: some("Fira Code"), fontSize: some(12), maxColumn: none };

// --- Law checks (run against the real representation) -----------------------

const holdsLaws = <A>(M: Monoid<A>, samples: ReadonlyArray<A>): boolean =>
  samples.every((x) =>
    [
      () => assert.deepEqual(M.concat(M.empty, x), x),
      () => assert.deepEqual(M.concat(x, M.empty), x),
      ...samples.flatMap((y) =>
        samples.map((z) => () =>
          assert.deepEqual(M.concat(M.concat(x, y), z), M.concat(x, M.concat(y, z))),
        ),
      ),
    ].every((check) => (check(), true)),
  );

assert.ok(holdsLaws(sum, [0, 1, -7, 42]));
assert.ok(holdsLaws(product, [1, 2, -3, 5]));
assert.ok(holdsLaws(bigSum, [0n, 1n, 10n ** 30n]));
assert.ok(holdsLaws(string, ["", "a", "bc"]));
assert.ok(holdsLaws(all, [true, false]));
assert.ok(holdsLaws(any, [true, false]));
assert.ok(holdsLaws(first<number>(), [none, some(1), some(2)]));
assert.ok(holdsLaws(last<number>(), [none, some(1), some(2)]));
assert.ok(holdsLaws(applicative(sum), [none, some(1), some(2)]));
assert.ok(holdsLaws(pointMonoid, [pointMonoid.empty, { x: 1, y: 2 }, { x: -3, y: 4 }]));

// Floating-point addition is NOT associative — never treat it as a lawful monoid.
assert.notEqual(sum.concat(sum.concat(0.1, 0.2), 0.3), sum.concat(0.1, sum.concat(0.2, 0.3)));

// `spaced` has no identity: the obvious candidate "" breaks it.
assert.notEqual(spaced.concat("a", ""), "a");

assert.equal(concatAll(sum)([1, 2, 3, 4]), 10);
assert.equal(concatAll(product)([1, 2, 3, 4]), 24);
assert.equal(concatAll(string)(["a", "b", "c"]), "abc");
assert.equal(concatAll(all)([true, false, true]), false);
assert.equal(concatAll(any)([true, false, true]), true);
assert.equal(concatAll(sum)([]), 0);

assert.deepEqual(applicative(sum).concat(some(1), none), none);
assert.deepEqual(applicative(sum).concat(some(1), some(2)), some(3));
assert.deepEqual(first<number>().concat(some(1), some(2)), some(1));
assert.deepEqual(last<number>().concat(some(1), some(2)), some(2));

assert.deepEqual(
  vectorMonoid.concat(
    { from: { x: 1, y: 1 }, to: { x: 2, y: 2 } },
    { from: { x: 1, y: 0 }, to: { x: 0, y: 1 } },
  ),
  { from: { x: 2, y: 1 }, to: { x: 2, y: 3 } },
);

assert.deepEqual(settingsMonoid.concat(workspace, user), {
  fontFamily: some("Fira Code"),
  fontSize: some(12),
  maxColumn: some(80),
});
