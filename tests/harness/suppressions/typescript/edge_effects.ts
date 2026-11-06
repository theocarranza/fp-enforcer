// Justified suppression: the production interpreter is the program edge,
// where ambient effects are supplied (fp-typescript effects 3).
// Expected: NO violations reported.
interface Console { readonly putStrLn: (message: string) => Promise<void> }
interface Random { readonly nextInt: (upper: number) => number }
export const liveConsole: Console = {
  putStrLn: (message) => Promise.resolve(console.log(message)), // fp-allow: no-ambient-effect — edge interpreter
};
export const liveRandom: Random = {
  nextInt: (upper) => 1 + Math.floor(Math.random() * upper), // fp-allow: no-ambient-effect — edge interpreter
};
