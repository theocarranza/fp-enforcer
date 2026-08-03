// Minimal dartz stand-ins so harness fixtures analyze without pub deps.
// Named .g.dart so the scanner excludes these declarations.
sealed class Either<L, R> {
  const Either();

  bool isLeft() => this is _Left<L, R>;

  bool isRight() => this is _Right<L, R>;

  B fold<B>(B Function(L) ifLeft, B Function(R) ifRight);
}

final class _Left<L, R> extends Either<L, R> {
  const _Left(this.value);

  final L value;

  @override
  B fold<B>(B Function(L) ifLeft, B Function(R) ifRight) => ifLeft(value);
}

final class _Right<L, R> extends Either<L, R> {
  const _Right(this.value);

  final R value;

  @override
  B fold<B>(B Function(L) ifLeft, B Function(R) ifRight) => ifRight(value);
}

Either<L, R> left<L, R>(L value) => _Left<L, R>(value);

Either<L, R> right<L, R>(R value) => _Right<L, R>(value);

sealed class Option<T> {
  const Option();

  bool isSome() => this is _Some<T>;

  bool isNone() => this is _None<T>;

  B fold<B>(B Function() ifNone, B Function(T) ifSome);
}

final class _Some<T> extends Option<T> {
  const _Some(this.value);

  final T value;

  @override
  B fold<B>(B Function() ifNone, B Function(T) ifSome) => ifSome(value);
}

final class _None<T> extends Option<T> {
  const _None();

  @override
  B fold<B>(B Function() ifNone, B Function(T) ifSome) => ifNone();
}

Option<T> some<T>(T value) => _Some<T>(value);

Option<T> none<T>() => _None<T>();

final class Task<A> {
  const Task(this._effect);

  final Future<A> Function() _effect;

  Future<A> run() => _effect();
}

final class Tuple2<T1, T2> {
  const Tuple2(this.first, this.second);

  final T1 first;

  final T2 second;
}
