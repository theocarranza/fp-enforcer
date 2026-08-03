// Minimal rxdart stand-ins so harness fixtures analyze without pub deps.
// Named .g.dart so the scanner excludes these declarations.
final class ReplaySubject<T> {
  ReplaySubject({int? maxSize});
}
