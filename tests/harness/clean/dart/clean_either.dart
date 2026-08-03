// Compliant: wrapped values consumed with fold (fp-core 11 / fp-dartz 2).
// Expected: NO violations reported.
import '../../stubs/dartz_stubs.g.dart';

String describe(Either<String, int> result) => result.fold(
      (failure) => 'failure: $failure',
      (value) => 'value: $value',
    );

int fallback(Option<int> value) => value.fold(() => 0, (v) => v);
