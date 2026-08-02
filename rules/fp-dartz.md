
# Dartz: The Functional Core

## Either (Error Handling)

1. Every Domain and Data layer method that can fail returns `Either<Failure, Success>`. Throwing for business errors is prohibited.
2. Consume with `.fold()` (or `.getOrElse`) — both cases handled explicitly. Reject `isLeft()`/`isRight()` unwrapping.
3. Validation railway: chain predicates with `.flatMap`; each step returns `right(Nothing())` or `left(ValidationFailure(...))`; first `Left` short-circuits.

## Option (Absence)

4. Reject `Option<T>` for simple absence — use native nullable (`?`). Reserve `Option` for composition chains requiring `.flatMap`.
5. At nullable boundaries, lift with `optionOf(nullable)`. Escape with `.toNullable()` only at framework/UI/external-API boundaries.
6. `map` when the callback returns a plain value; `flatMap`/`bind` when it returns `Option`; `orElse` to recover from `None`; `toEither(() => failure)` when absence becomes a domain failure; `Option.mapN` to combine multiple optionals.

## Task (Deferred Effects)

7. Side-effecting futures go through the canonical chain — never `try/catch` in a use case:

```dart
Task(() => sideEffectingCall())      // pure thunk; nothing runs yet
    .attempt()                       // Task<Either<Object, A>>
    .mapLeft<Failure>((e) => DomainFailure(innerError: e, innerMessage: '$e'))
    .mapRight((a) => mapToDomain(a))
    .run();                          // materialize ONLY at the boundary
```

8. Never `await` inside a `Task` builder — the thunk builds the future lazily.
9. `Task.value`/`Task.failed` over hand-wrapped resolved futures; `flatMap` for callbacks returning `Task`; `flatTap` for logging/telemetry without altering the value.
10. Sequence by default (`Task.map2`, `tupled`); go parallel (`parMap`, `parTupled`, `both`) only when tasks are truly independent.
11. `bracket`/`guarantee` over manual `try/finally` for resource lifetimes. `ifM` over imperative branching on a `Task<bool>`.
12. `run()` re-executes the thunk every call — no memoization assumptions. `race` losers keep running; Futures don't cancel.

## Types & Collections

13. Reject `Tuple` in return types — use a named `record` or dedicated class.
14. `IList`/`IMap` stay immutable; convert to native collections only at the UI boundary.
