// Violates: fp-core branching 2 — else / else if branches.
// Expected: CAUGHT by no-else.
String classify(int score) {
  if (score > 90) {
    return 'gold';
  } else if (score > 50) {
    return 'silver';
  } else {
    return 'bronze';
  }
}
