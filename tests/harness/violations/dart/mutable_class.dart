// Violates: fp-dart-style design 1-2 — mutable public fields, late binding,
// missing const constructor.
// Expected: MISSED — no pattern exists.
class UserProfile {
  String name;
  late int age;

  UserProfile(this.name);
}
