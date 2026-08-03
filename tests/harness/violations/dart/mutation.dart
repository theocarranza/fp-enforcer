// Violates: fp-core data 1 / fp-dartz 14 — reassignment and mutation of
// bindings and collections.
// Expected: MISSED — no pattern exists.
class Counter {
  int value = 0;

  int bump() {
    value = value + 1;
    return value;
  }
}

List<int> appendAll(List<int> base, List<int> extra) {
  base.addAll(extra);
  base.sort();
  return base;
}
