// fp-ts to the max, part I — a Task program with Option parsing (fp-ts 2.16+).
// Library-agnostic form: ../../examples/typescript/effects-as-capabilities.ts
//
// fp-ts idioms shown: T.Do + T.apS (named scope), T.tap (keep value, run effect),
// T.flatMap chains, O.match to consume Option, recursion instead of loops.

import * as C from "fp-ts/Console";
import { flow, pipe } from "fp-ts/function";
import * as O from "fp-ts/Option";
import { randomInt } from "fp-ts/Random";
import * as T from "fp-ts/Task";
import { createInterface } from "node:readline/promises";

const getStrLn: T.Task<string> = () =>
  ((rl) => rl.question("> ").finally(() => rl.close()))(
    createInterface({ input: process.stdin, output: process.stdout }), // fp-allow: no-ambient-effect — edge interpreter
  );

const putStrLn = flow(C.log, T.fromIO);

const ask = (question: string): T.Task<string> =>
  pipe(
    putStrLn(question),
    T.flatMap(() => getStrLn),
  );

const random = T.fromIO(randomInt(1, 5));

const parse = (s: string): O.Option<number> =>
  s.trim() !== "" && Number.isInteger(Number(s)) ? O.some(Number(s)) : O.none;

const shouldContinue = (name: string): T.Task<boolean> =>
  pipe(
    ask(`Do you want to continue, ${name} (y/n)?`),
    T.flatMap((answer) => {
      switch (answer.toLowerCase()) {
        case "y":
          return T.of(true);
        case "n":
          return T.of(false);
        default:
          return shouldContinue(name);
      }
    }),
  );

const gameLoop = (name: string): T.Task<void> =>
  pipe(
    T.Do,
    T.apS("secret", random),
    T.apS("guess", ask(`Dear ${name}, please guess a number from 1 to 5`)),
    T.flatMap(({ secret, guess }) =>
      pipe(
        parse(guess),
        O.match(
          () => putStrLn("You did not enter an integer!"),
          (x) =>
            x === secret
              ? putStrLn(`You guessed right, ${name}!`)
              : putStrLn(`You guessed wrong, ${name}! The number was: ${secret}`),
        ),
      ),
    ),
    T.flatMap(() => shouldContinue(name)),
    T.flatMap((again) => (again ? gameLoop(name) : T.of(undefined))),
  );

/** Run once at the program edge: `await main()`. */
export const main: T.Task<void> = pipe(
  ask("What is your name?"),
  T.tap((name) => putStrLn(`Hello, ${name} welcome to the game!`)),
  T.flatMap(gameLoop),
);
