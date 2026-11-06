// fp-ts to the max, part II — tagless final with fp-ts HKTs (fp-ts 2.16+).
// Library-agnostic form: ../../examples/typescript/effects-as-capabilities.ts
//
// The program is written once against Program/Console/Random capabilities and
// interpreted twice: Task in production, State<TestData, _> in tests.

import assert from "node:assert/strict";
import { createInterface } from "node:readline/promises";
import { apS as apS_ } from "fp-ts/Apply";
import { chainFirst as chainFirst_ } from "fp-ts/Chain";
import * as C from "fp-ts/Console";
import { flow, pipe } from "fp-ts/function";
import type { Kind, URIS } from "fp-ts/HKT";
import type { Monad1 } from "fp-ts/Monad";
import * as O from "fp-ts/Option";
import { randomInt } from "fp-ts/Random";
import * as S from "fp-ts/State";
import * as T from "fp-ts/Task";

// --- capabilities (type classes) ---------------------------------------------

interface Program<F extends URIS> extends Monad1<F> {
  readonly finish: <A>(a: A) => Kind<F, A>;
}

interface Console<F extends URIS> {
  readonly putStrLn: (message: string) => Kind<F, void>;
  readonly getStrLn: Kind<F, string>;
}

interface Random<F extends URIS> {
  readonly nextInt: (upper: number) => Kind<F, number>;
}

interface Main<F extends URIS> extends Program<F>, Console<F>, Random<F> {}

// --- the program, written once ----------------------------------------------

const parse = (s: string): O.Option<number> =>
  s.trim() !== "" && Number.isInteger(Number(s)) ? O.some(Number(s)) : O.none;

const main = <F extends URIS>(F: Main<F>): Kind<F, void> => {
  const flatMap =
    <A, B>(f: (a: A) => Kind<F, B>) =>
    (ma: Kind<F, A>): Kind<F, B> =>
      F.chain(ma, f);
  const Do: Kind<F, {}> = F.of({});
  const apS = apS_(F);
  const tap = chainFirst_(F);

  const ask = (question: string): Kind<F, string> =>
    pipe(
      F.putStrLn(question),
      flatMap(() => F.getStrLn),
    );

  const shouldContinue = (name: string): Kind<F, boolean> =>
    pipe(
      ask(`Do you want to continue, ${name} (y/n)?`),
      flatMap((answer) => {
        switch (answer.toLowerCase()) {
          case "y":
            return F.of<boolean>(true);
          case "n":
            return F.of<boolean>(false);
          default:
            return shouldContinue(name);
        }
      }),
    );

  const gameLoop = (name: string): Kind<F, void> =>
    pipe(
      Do,
      apS("secret", F.nextInt(5)),
      apS("guess", ask(`Dear ${name}, please guess a number from 1 to 5`)),
      flatMap(({ secret, guess }) =>
        pipe(
          parse(guess),
          O.match(
            () => F.putStrLn("You did not enter an integer!"),
            (x) =>
              x === secret
                ? F.putStrLn(`You guessed right, ${name}!`)
                : F.putStrLn(`You guessed wrong, ${name}! The number was: ${secret}`),
          ),
        ),
      ),
      flatMap(() => shouldContinue(name)),
      flatMap((again) => (again ? gameLoop(name) : F.of<void>(undefined))),
    );

  return pipe(
    ask("What is your name?"),
    tap((name) => F.putStrLn(`Hello, ${name} welcome to the game!`)),
    flatMap(gameLoop),
  );
};

// --- production interpreter: Task ------------------------------------------

const getStrLn: T.Task<string> = () =>
  ((rl) => rl.question("> ").finally(() => rl.close()))(
    createInterface({ input: process.stdin, output: process.stdout }), // fp-allow: no-ambient-effect — edge interpreter
  );

/** Run once at the program edge: `await mainTask()`. */
export const mainTask = main<T.URI>({
  ...T.Monad,
  finish: T.of,
  putStrLn: flow(C.log, T.fromIO),
  getStrLn,
  nextInt: (upper) => T.fromIO(randomInt(1, upper)),
});

// --- test interpreter: State<TestData, _> -------------------------------------

type TestData = {
  readonly input: ReadonlyArray<string>;
  readonly output: ReadonlyArray<string>;
  readonly nums: ReadonlyArray<number>;
};

const URI = "Test";
type URI = typeof URI;

declare module "fp-ts/HKT" {
  interface URItoKind<A> {
    readonly Test: Test<A>;
  }
}

interface Test<A> extends S.State<TestData, A> {}

const mainTest = main<URI>({
  ...S.Monad,
  URI,
  finish: S.of,
  putStrLn: (message) => (s) => [undefined, { ...s, output: [...s.output, message] }],
  getStrLn: (s) => [s.input[0] ?? "", { ...s, input: s.input.slice(1) }],
  nextInt: () => (s) => [s.nums[0] ?? 1, { ...s, nums: s.nums.slice(1) }],
});

assert.deepEqual(mainTest({ input: ["Giulio", "1", "n"], output: [], nums: [1] }), [
  undefined,
  {
    input: [],
    output: [
      "What is your name?",
      "Hello, Giulio welcome to the game!",
      "Dear Giulio, please guess a number from 1 to 5",
      "You guessed right, Giulio!",
      "Do you want to continue, Giulio (y/n)?",
    ],
    nums: [],
  },
]);
