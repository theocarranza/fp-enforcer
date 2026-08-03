// Compliant: readonly fields with constructor initialization — the this.
// receiver is excluded from no-field-write by design (fp-typescript 1 & 6).
// Expected: NO violations reported.
export class UserProfile {
  readonly name: string;
  readonly age: number;

  constructor(name: string, age: number) {
    this.name = name;
    this.age = age;
  }
}

export const rename = (
  user: UserProfile,
  name: string,
): UserProfile => new UserProfile(name, user.age);
