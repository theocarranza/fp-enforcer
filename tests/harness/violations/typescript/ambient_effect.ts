// Violates: fp-typescript effects 1 — domain code reaches for ambient effects
// instead of receiving them as injected capabilities.
// Expected: no-ambient-effect.
export const roll = (): number => 1 + Math.floor(Math.random() * 6);
export const stamp = (): number => Date.now();
export const today = (): string => new Date().toISOString();
export const greet = (name: string): void => console.log(`hi ${name}`);
export const isDebug = (): boolean => process.env.DEBUG === "1";
