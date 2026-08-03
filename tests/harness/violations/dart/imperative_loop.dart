// Violates: fp-core data 4 / fp-dart-style usage 2 — imperative loops over
// collections instead of map/where/fold/expand.
// Expected: MISSED — no pattern exists.
List<int> doubled(List<int> values) {
  final result = <int>[];
  for (final value in values) {
    result.add(value * 2);
  }
  return result;
}

int countMatching(List<int> values) {
  var count = 0;
  while (values.isNotEmpty) {
    count += 1;
    break;
  }
  return count;
}
