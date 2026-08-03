// Compliant: Future<void> with explicit await (fp-dart-style asynchrony 1).
// Expected: NO violations reported.
Future<void> saveDraft() async {
  await Future<void>.delayed(const Duration(milliseconds: 1));
}
