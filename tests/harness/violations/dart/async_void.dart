// Violates: fp-dart-style asynchrony 1 — async void instead of Future<void>.
// Expected: CAUGHT by no-async-void.
void saveDraft() async {
  await Future<void>.delayed(const Duration(milliseconds: 1));
}
