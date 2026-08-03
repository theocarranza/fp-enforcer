// Compliant: genuine boolean OR is not an absence fallback — the
// no-or-fallback pattern only fires when the right side is a literal
// (fp-typescript 3, contrast fp-flutter performance 4).
// Expected: NO violations reported.
export const canAccess = (flags: {
  readonly isActive: boolean;
  readonly isAdmin: boolean;
}): boolean => flags.isActive || flags.isAdmin;
