// Violates: fp-rxdart memory safety 2 — ReplaySubject without maxSize bound.
// Expected: MISSED — no pattern exists.
import '../../stubs/rxdart_stubs.g.dart';

class EventBus {
  final ReplaySubject<String> events = ReplaySubject<String>();
}
