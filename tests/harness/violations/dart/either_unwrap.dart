// Violates: fp-core branching 4 / fp-dartz 2 — unwrapping instead of fold.
// Expected: CAUGHT by fold-not-unwrap.
import '../../stubs/dartz_stubs.g.dart';

String describe(Either<String, int> result) {
  if (result.isLeft()) {
    return 'failure';
  }
  return 'success';
}

bool present(Option<int> value) {
  return value.isSome();
}
