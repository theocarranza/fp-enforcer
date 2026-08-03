// Compliant: platform-crash exception types are reserved for the
// unexpected (fp-core 5) and allowlisted by no-throw-domain.
// Expected: NO violations reported.
Never unsupported(String feature) =>
    throw UnimplementedError('$feature is not supported yet');
