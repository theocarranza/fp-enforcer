// Violates: fp-dartz 13 — Tuple in a return type instead of a record/class.
// Expected: CAUGHT by no-tuple-return.
import '../../stubs/dartz_stubs.g.dart';

Tuple2<String, int> splitName(String fullName) {
  final parts = fullName.split(' ');
  return Tuple2(parts.first, parts.length);
}
