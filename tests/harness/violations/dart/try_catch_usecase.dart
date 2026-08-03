// Violates: fp-dartz 7 — try/catch in a use case instead of Task().attempt().
// Expected: CAUGHT by no-try-catch.
import '../../stubs/dartz_stubs.g.dart';

class FetchUser {
  Future<Either<Object, String>> call() async {
    try {
      final response = await _fetch();
      return right(response);
    } catch (e) {
      return left(e);
    }
  }

  Future<String> _fetch() async => 'user';
}
