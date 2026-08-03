// Violates: fp-core errors 1 / fp-dartz 1 — throwing for business errors
// instead of returning Either<Failure, T>.
// Expected: MISSED — no pattern exists.
String requireName(Map<String, String> payload) {
  final name = payload['name'];
  if (name == null) {
    throw ArgumentError('name is required');
  }
  return name;
}
