// Compliant: immutable class, final fields, const constructor
// (fp-dart-style design 1-2).
// Expected: NO violations reported.
final class UserProfile {
  const UserProfile({required this.name, required this.age});

  final String name;
  final int age;
}
