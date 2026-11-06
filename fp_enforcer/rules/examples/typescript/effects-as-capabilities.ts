// Effects as capabilities — one program, many interpreters (plain TypeScript).
// Run: node fp_enforcer/rules/examples/typescript/effects-as-capabilities.ts  (Node >= 22.6)
//
// Principle: a program never reaches for the console, the clock or the RNG.
// It declares the capabilities it needs, is written ONCE against them, and is
// handed an interpreter at the edge: real effects in production, a pure
// state-threading interpreter in tests. Repetition is recursion; raw input is
// parsed into Option at the boundary and consumed exactly once.
//
// The generic (higher-kinded) form below pays for itself because there are
// two real interpreters. With a single interpreter, inject a plain record of
// functions instead (e.g. `interface Clock { readonly now: () => Date }`).

import assert from "node:assert/strict";
import { createInterface } from "node:readline/promises";

// --- Higher-kinded types without a library ----------------------------------
// A registry maps an effect name to its type constructor. Interpreters add
// entries; programs stay generic over `F extends Kind`.

type Task<A> = () => Promise<A>;
type State<S, A> = (s: S) => readonly [A, S];

interface Kinds<A> {
  readonly Task: Task<A>;
  readonly Test: State<TestData, A>;
}
type Kind = keyof Kinds<unknown>;
type HKT<F extends Kind, A> = Kinds<A>[F];

// --- Capabilities -----------------------------------------------------------

interface Monad<F extends Kind> {
  readonly of: <A>(a: A) => HKT<F, A>;
  readonly flatMap: <A, B>(fa: HKT<F, A>, f: (a: A) => HKT<F, B>) => HKT<F, B>;
}

interface Console<F extends Kind> {
  readonly putStrLn: (message: string) => HKT<F, void>;
  readonly getStrLn: HKT<F, string>;
}

interface Random<F extends Kind> {
  readonly nextInt: (upper: number) => HKT<F, number>;
}

/** Capabilities compose by intersection; the program asks for exactly these. */
type Main<F extends Kind> = Monad<F> & Console<F> & Random<F>;

// --- Pure helpers -----------------------------------------------------------

type Option<A> = { readonly _tag: "None" } | { readonly _tag: "Some"; readonly value: A };
const none: Option<never> = { _tag: "None" };
const some = <A>(value: A): Option<A> => ({ _tag: "Some", value });

const foldOption =
  <A, B>(onNone: () => B, onSome: (a: A) => B) =>
  (oa: Option<A>): B => {
    switch (oa._tag) {
      case "None":
        return onNone();
      case "Some":
        return onSome(oa.value);
    }
  };

/** Parse, don't validate: the boundary turns raw text into Option<number>. */
const parseInteger = (s: string): Option<number> =>
  s.trim() !== "" && Number.isInteger(Number(s)) ? some(Number(s)) : none;

// --- The program, written once ----------------------------------------------

const program = <F extends Kind>(F: Main<F>): HKT<F, void> => {
  /** Run an effect for its side effect, keep the original value. */
  const tap =
    <A>(f: (a: A) => HKT<F, unknown>) =>
    (fa: HKT<F, A>): HKT<F, A> =>
      F.flatMap(fa, (a) => F.flatMap(f(a), () => F.of(a)));

  const ask = (question: string): HKT<F, string> =>
    F.flatMap(F.putStrLn(question), () => F.getStrLn);

  /** Repetition is recursion: invalid input re-asks by returning itself. */
  const shouldContinue = (name: string): HKT<F, boolean> =>
    F.flatMap(ask(`Do you want to continue, ${name} (y/n)?`), (answer) => {
      switch (answer.toLowerCase()) {
        case "y":
          return F.of(true);
        case "n":
          return F.of(false);
        default:
          return shouldContinue(name);
      }
    });

  const verdict = (name: string, secret: number) =>
    foldOption<number, HKT<F, void>>(
      () => F.putStrLn("You did not enter an integer!"),
      (guess) =>
        F.putStrLn(
          guess === secret
            ? `You guessed right, ${name}!`
            : `You guessed wrong, ${name}! The number was: ${secret}`,
        ),
    );

  const gameLoop = (name: string): HKT<F, void> =>
    F.flatMap(F.nextInt(5), (secret) =>
      F.flatMap(ask(`Dear ${name}, please guess a number from 1 to 5`), (guess) =>
        F.flatMap(verdict(name, secret)(parseInteger(guess)), () =>
          F.flatMap(shouldContinue(name), (again) =>
            again ? gameLoop(name) : F.of<void>(undefined),
          ),
        ),
      ),
    );

  return F.flatMap(
    tap((name: string) => F.putStrLn(`Hello, ${name} welcome to the game!`))(
      ask("What is your name?"),
    ),
    gameLoop,
  );
};

// --- Interpreter 1: production (real effects, run once at the edge) ----------

const readLine = (rl: ReturnType<typeof createInterface>): Promise<string> =>
  rl.question("> ").finally(() => rl.close());

const live: Main<"Task"> = {
  of: (a) => () => Promise.resolve(a),
  flatMap: (fa, f) => () => fa().then((a) => f(a)()),
  putStrLn: (message) => () => Promise.resolve(console.log(message)), // fp-allow: no-ambient-effect — edge interpreter
  getStrLn: () => readLine(createInterface({ input: process.stdin, output: process.stdout })), // fp-allow: no-ambient-effect — edge interpreter
  nextInt: (upper) => () => Promise.resolve(1 + Math.floor(Math.random() * upper)), // fp-allow: no-ambient-effect — edge interpreter
};

/** The single effectful invocation lives at the program edge: `await main()`. */
export const main: Task<void> = program(live);

// --- Interpreter 2: tests (pure state threading, no I/O, no mocks) -----------

type TestData = {
  readonly input: ReadonlyArray<string>;
  readonly output: ReadonlyArray<string>;
  readonly nums: ReadonlyArray<number>;
};

const test: Main<"Test"> = {
  of: (a) => (s) => [a, s],
  flatMap: (fa, f) => (s) => {
    const [a, next] = fa(s);
    return f(a)(next);
  },
  putStrLn: (message) => (s) => [undefined, { ...s, output: [...s.output, message] }],
  getStrLn: (s) => [s.input[0] ?? "", { ...s, input: s.input.slice(1) }],
  nextInt: () => (s) => [s.nums[0] ?? 1, { ...s, nums: s.nums.slice(1) }],
};

assert.deepEqual(program(test)({ input: ["Giulio", "1", "x", "n"], output: [], nums: [1] }), [
  undefined,
  {
    input: [],
    output: [
      "What is your name?",
      "Hello, Giulio welcome to the game!",
      "Dear Giulio, please guess a number from 1 to 5",
      "You guessed right, Giulio!",
      "Do you want to continue, Giulio (y/n)?",
      "Do you want to continue, Giulio (y/n)?",
    ],
    nums: [],
  },
]);

assert.deepEqual(parseInteger("42"), some(42));
assert.deepEqual(parseInteger("4.2"), none);
assert.deepEqual(parseInteger(""), none);
