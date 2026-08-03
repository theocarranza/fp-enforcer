// Compliant: higher-order collection methods over loops and mutation
// (fp-core 12 & 15 / fp-dart-style usage 2).
// Expected: NO violations reported.
List<int> doubled(List<int> values) =>
    values.map((value) => value * 2).toList();

List<int> evens(List<int> values) =>
    values.where((value) => value.isEven).toList();

int total(List<int> values) => values.fold(0, (sum, value) => sum + value);
