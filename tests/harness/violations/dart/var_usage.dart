// Violates: fp-dart-style usage 1 — var locals instead of final/const.
// Expected: CAUGHT by no-var.
int total(List<int> values) {
  var sum = 0;
  for (var value in values) {
    sum += value;
  }
  return sum;
}
