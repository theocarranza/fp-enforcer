// Violates: fp-rxdart stream composition 1 — manual .listen() inside
// business logic instead of declarative operators.
// Expected: MISSED — no pattern exists.
import 'dart:async';

class SearchBloc {
  final StreamController<String> _queries = StreamController<String>();

  void bind() {
    _queries.stream.listen((query) {
      _search(query);
    });
  }

  Future<void> _search(String query) async {}
}
