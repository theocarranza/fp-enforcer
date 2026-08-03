// Compliant: effects deferred in Task, materialized with run() only at the
// boundary (fp-core 3 / fp-dartz 7).
// Expected: NO violations reported.
import '../../stubs/dartz_stubs.g.dart';

final class UserGateway {
  const UserGateway();

  Task<String> fetch() => Task(() async => 'user');
}

Future<String> runBoundary() => const UserGateway().fetch().run();
