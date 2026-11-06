// Monoids with fp-ts (2.16+), current API names.
// Library-agnostic form: ../../examples/typescript/monoids.ts
//
// Renames from older tutorials:
//   getStructMonoid        -> M.struct
//   M.fold                 -> M.concatAll
//   O.getFirstMonoid()     -> O.getMonoid(Sg.first())
//   O.getLastMonoid()      -> O.getMonoid(Sg.last())
//   O.getApplyMonoid(M)    -> getApplicativeMonoid(O.Applicative)(M)

import assert from "node:assert/strict";
import { getApplicativeMonoid } from "fp-ts/Applicative";
import * as B from "fp-ts/boolean";
import * as M from "fp-ts/Monoid";
import * as N from "fp-ts/number";
import * as O from "fp-ts/Option";
import * as Sg from "fp-ts/Semigroup";
import * as Str from "fp-ts/string";

// Built-in instances: N.MonoidSum, N.MonoidProduct, Str.Monoid, B.MonoidAll, B.MonoidAny.
assert.equal(M.concatAll(N.MonoidSum)([1, 2, 3, 4]), 10);
assert.equal(M.concatAll(N.MonoidProduct)([1, 2, 3, 4]), 24);
assert.equal(M.concatAll(Str.Monoid)(["a", "b", "c"]), "abc");
assert.equal(M.concatAll(B.MonoidAll)([true, false, true]), false);
assert.equal(M.concatAll(B.MonoidAny)([true, false, true]), true);

// Struct monoids derive field-wise and nest.
type Point = { readonly x: number; readonly y: number };
type Vector = { readonly from: Point; readonly to: Point };
const MPoint: M.Monoid<Point> = M.struct({ x: N.MonoidSum, y: N.MonoidSum });
const MVector: M.Monoid<Vector> = M.struct({ from: MPoint, to: MPoint });
assert.deepEqual(MVector.empty, { from: { x: 0, y: 0 }, to: { x: 0, y: 0 } });

// Option: applicative (None absorbs), first, last.
const MApply = getApplicativeMonoid(O.Applicative)(N.MonoidSum);
assert.deepEqual(MApply.concat(O.some(1), O.none), O.none);
assert.deepEqual(MApply.concat(O.some(1), O.some(2)), O.some(3));
assert.deepEqual(MApply.concat(O.some(1), MApply.empty), O.some(1));

const MFirst = O.getMonoid<number>(Sg.first());
const MLast = O.getMonoid<number>(Sg.last());
assert.deepEqual(MFirst.concat(O.some(1), O.some(2)), O.some(1));
assert.deepEqual(MLast.concat(O.some(1), O.some(2)), O.some(2));

// Settings overrides: user beats workspace field by field.
type Settings = {
  readonly fontFamily: O.Option<string>;
  readonly fontSize: O.Option<number>;
  readonly maxColumn: O.Option<number>;
};
const MSettings: M.Monoid<Settings> = M.struct({
  fontFamily: O.getMonoid<string>(Sg.last()),
  fontSize: O.getMonoid<number>(Sg.last()),
  maxColumn: O.getMonoid<number>(Sg.last()),
});
assert.deepEqual(
  MSettings.concat(
    { fontFamily: O.some("Courier"), fontSize: O.none, maxColumn: O.some(80) },
    { fontFamily: O.some("Fira Code"), fontSize: O.some(12), maxColumn: O.none },
  ),
  { fontFamily: O.some("Fira Code"), fontSize: O.some(12), maxColumn: O.some(80) },
);
