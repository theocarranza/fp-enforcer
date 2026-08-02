
# RxDart: The Reactive Flow

## Stream Composition

1. Declarative mandate: reject manual `.listen()` inside business logic. Compose output streams from input streams with operators (`map`, `switchMap`, `combineLatest`).
2. Operator discipline:
   - `debounceTime` mandatory for user input (~400ms for input-driven queries — prevents per-keystroke calls and rebuild storms).
   - `distinctUnique` mandatory to prevent redundant emission processing.
   - `switchMap` mandatory for network requests, to cancel stale calls.

## Memory Safety

3. When `.listen()` is unavoidable (UI edge), bind the subscription to a `CompositeSubscription` or a flutter_hook that guarantees disposal.
4. Subject restrictions:
   - `BehaviorSubject`: approved for state holding (current-value access).
   - `PublishSubject`: approved for events (clicks, toasts).
   - `ReplaySubject`: restricted — explicit `maxSize` bounds only.
