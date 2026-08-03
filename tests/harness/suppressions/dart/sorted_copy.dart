// Justified suppression: sorting a fresh copy is externally pure — the
// mutation is invisible to callers, so the tripwire is waived with cause.
// Expected: NO violations reported.
List<int> sortedCopy(List<int> values) =>
    // fp-allow: no-collection-mutation — mutates a fresh copy, externally pure
    List<int>.of(values)..sort();
