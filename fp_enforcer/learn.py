"""Detect functional libraries and emit agent-facing knowledge profiles."""

from __future__ import annotations

import json
import re
from pathlib import Path

_PUBSPEC_RE = re.compile(r"^\s+(dartz|fpdart|rxdart):", re.MULTILINE)
_NODE_LIBRARIES: frozenset[str] = frozenset({"fp-ts", "effect", "rxjs"})

PROFILES: dict[str, str] = {
    "dartz": """# Dartz — Functional Dart Reference

## Types

- **Either<L, R>**: typed success/failure; `Left` is failure, `Right` is success.
- **Option<A>**: explicit absence instead of nullable references; prefer `some`/`none`.
- **Task<A>**: deferred synchronous effect; build pipelines, call `.run()` only at edges.
- **IList / IMap**: immutable collections at domain boundaries; convert from mutable lists/maps at the gateway.

## Operators

- **fold**: the only way to consume `Either` and `Option`; never branch on `isLeft`/`isRight`/`isSome`/`isNone`.
- **flatMap (bind)**: chain steps that can fail; first `Left`/`None` short-circuits the railway.
- **map / mapLeft**: transform success or failure payloads without unwrapping.
- **Task(...).attempt().mapLeft(...).run()**: canonical effect chain — defer work, capture exceptions as `Either`, map failures, execute once at the boundary.

## Composition idioms

- Validation railway: `validateA.flatMap(validateB).flatMap(validateC)` — each validator returns `Either<Failure, T>`.
- Option pipelines: `option.flatMap(findUser).flatMap(loadProfile).fold(() => default, useProfile)`.
- Replace nullable checks with `optionOf(value)` and `fold`; model "missing" as `none()`.
- Boundary rule: accept `List`/`Map` from Flutter/Firebase, immediately wrap to `IList`/`IMap` for pure domain code.

## Do / Don't

- **Do** return `Either<Failure, T>` from anything that can fail; handle every `Left` explicitly.
- **Do** use `fold` for all branching on `Either` and `Option`.
- **Do** keep `Task.run()` in controllers, repositories, and `main` — one invocation per call site.
- **Don't** return `Tuple2`/`Tuple3` for multi-outcome results — use a sealed ADT or named record type.
- **Don't** use `try/catch` for business validation; use `Task.attempt()` at IO boundaries only.
- **Don't** thread loggers through pure functions; log at named boundary methods after `fold`.
""",
    "fpdart": """# FPDart — Functional Dart Reference

## Types

- **Either<L, R>**: railway-oriented error handling; same role as dartz `Either`.
- **Option<A>**: replaces nullable semantics with explicit `Some`/`None`.
- **Task<A>**: lazy synchronous effect container.
- **TaskEither<L, R>**: combines deferred execution with typed failure — primary effect type for IO.

## Operators

- **flatMap / map / mapLeft**: identical railway semantics to dartz; chain with `flatMap`, never early-return ladders.
- **fold**: mandatory consumer for `Either`, `Option`, and `TaskEither` results.
- **getOrElse / orElse**: recover from `Option` at the edge only, not inside pure transforms.
- **Do notation (`Do`, `$`)**: sequential binding for readable multi-step pipelines without nested `flatMap`.

## Composition idioms

- `TaskEither.tryCatch(() => io(), onError)` at repository boundaries; pure domain stays `Either`-only.
- Do-block validation:
  ```
  final result = TaskEither.Do(($) async {
    final a = $(stepA);
    final b = $(stepB);
    return combine(a, b);
  });
  ```
- Option + Either interop: lift `Option` failures into `Either` with `toEither(() => failure)`.
- Prefer `Record` or sealed classes over tuples for multi-field success values.

## Do / Don't

- **Do** use `TaskEither` for any async IO that can fail (network, disk, platform channels).
- **Do** compose with `flatMap` and Do notation; keep each step a named pure function where possible.
- **Do** run effects exactly once at the program edge via `.run()` or `.getOrElse(...)`.
- **Don't** mix imperative `try/catch` with railway code in the same layer.
- **Don't** unwrap with `isLeft`/`isRight`; always `fold`.
- **Don't** store mutable state inside Task pipelines; pass immutable snapshots forward.
""",
    "rxdart": """# RxDart — Reactive Dart Reference

## Types

- **BehaviorSubject<T>**: holds and replays the latest value — use for **state** (current user, theme, form snapshot).
- **PublishSubject<T>**: no initial value, emits only new events — use for **discrete events** (button taps, one-shot signals).
- **ReplaySubject<T>**: bounded history replay — use only with a **small, fixed buffer** for late subscribers (never unbounded).
- **CompositeSubscription**: aggregate disposables; dispose once when the owning widget/controller tears down.

## Operators

- **debounceTime**: coalesce rapid input (search fields, resize) before downstream work.
- **distinctUnique** (or `distinct()` with key): suppress duplicate consecutive emissions.
- **switchMap**: cancel prior inner streams — mandatory for network/search; never `flatMap` open-ended requests.
- **map / where**: pure transforms on the stream; keep side effects out of operators.
- **startWith / shareValue**: seed BehaviorSubject-driven UI and avoid duplicate upstream subscriptions.

## Composition idioms

- State: `BehaviorSubject.seeded(initial)` → `distinctUnique()` → `debounceTime(300.ms)` → UI `StreamBuilder`.
- Events: `PublishSubject<Event>()` → `where` filters → `switchMap` to `Task`/repository → `fold` results back to subject.
- Combine latest: `Rx.combineLatest2(a, b, combiner)` for derived state without manual mutation.
- Disposal: collect every `StreamSubscription` into `CompositeSubscription`; call `clear()` in `dispose()`.

## Do / Don't

- **Do** use `BehaviorSubject` for state and `PublishSubject` for fire-and-forget events.
- **Do** bound `ReplaySubject` buffers; prefer `BehaviorSubject` when only the latest value matters.
- **Do** use `switchMap` for any stream that triggers async work that can be superseded.
- **Don't** leak subscriptions — every listen must have a matching cancel/dispose path.
- **Don't** mutate shared objects inside `map`; emit new immutable values.
- **Don't** use subjects as global mutable bags; scope them to feature modules or providers.
""",
    "fp-ts": """# FP-TS — Functional TypeScript Reference

## Types

- **Either<E, A>**: typed errors; `left`/`right` constructors; primary railway type.
- **Option<A>**: `some`/`none` instead of `null`/`undefined` in domain code.
- **Task<A>**: lazy sync effect; **TaskEither<E, A>** for async IO with failure channel.
- **Monoid<A>**: `{ concat: (x, y) => A; empty: A }` — algebraic aggregation with identity.

## Operators

- **pipe / flow**: left-to-right composition; `pipe(value, f, g, h)` replaces nested calls.
- **flatMap / map / mapLeft / fold**: standard railway operators; `fold` is the only exit.
- **getStructMonoid**: derive a monoid for records — field-wise `concat` with defaults.
- **getLastMonoid**: last-write-wins merge for settings/overrides.
- **concatAll / fold (Monoid)**: replace accumulator loops with `concat` chains ending at `empty`.

## Composition idioms

- Validation: `pipe(input, validateName, flatMap(validateAge), flatMap(save))`.
- Monoid aggregation: `pipe(items, concatAll(monoid), normalize)` instead of `for (const x of items) acc = ...`.
- Struct settings merge: `pipe(defaults, concat(getStructMonoid({...})(partial)))`.
- TaskEither pipeline: `pipe(task, flatMap(fetch), map(parse), mapLeft(toDomainError))` then `run()` at handler edge.

## Do / Don't

- **Do** use `pipe` for every multi-step transform; extract named functions when a step exceeds one expression.
- **Do** model aggregations with `Monoid` — define `concat` + `empty`, then `fold` or `concatAll`.
- **Do** use `getLastMonoid` when later values override earlier ones (config patches, feature flags).
- **Don't** use `if/else` ladders for validation; chain `flatMap` and let the first `left` short-circuit.
- **Don't** unwrap `Either` with type guards; always `fold`.
- **Don't** mutate external state inside `map`; return new values.
""",
    "effect": """# Effect — TypeScript Effect System Reference

## Types

- **Effect<R, E, A>**: deferred computation with requirements `R`, failure `E`, success `A`.
- **Layer**: composable dependency injection — wire implementations to interfaces.
- **Context / Tag**: typed service locator keys for layers.

## Operators

- **pipe**: compose `Effect` transforms left-to-right.
- **flatMap / map / mapError**: railway chaining on the success and error channels.
- **provide / provideLayer**: satisfy `R` at the edge by supplying layers.
- **runPromise / runSync**: execute at boundaries (handlers, CLI, tests) only.

## Composition idioms

- Service definition: `Context.Tag<Service>()("Service")` + `Layer.effect` implementation.
- App wiring: `pipe(program, provideLayer(AppLive), runPromise)` in `main`.
- Error channel: map platform exceptions to domain errors with `mapError` before crossing module boundaries.

## Do / Don't

- **Do** keep business logic in pure `Effect` pipelines; provide layers once at startup.
- **Do** use typed error channels instead of thrown exceptions for expected failures.
- **Don't** call `runPromise` inside pure domain helpers — one run per request/handler.
- **Don't** mix untyped `Promise` chains with `Effect` in the same module without lifting.
""",
    "rxjs": """# RxJS — Reactive TypeScript Reference

## Types

- **BehaviorSubject<T>**: state container with current value — mirrors RxDart `BehaviorSubject` for UI/state.
- **Subject / PublishSubject pattern**: emit discrete events without replaying history.
- **ReplaySubject**: only with explicit buffer size for bounded replay to late subscribers.
- **Subscription**: disposable handle; aggregate and unsubscribe on teardown.

## Operators

- **debounceTime**: delay emissions until input pauses — search boxes, form validation triggers.
- **distinctUntilChanged**: skip consecutive duplicates (RxJS name for distinct-by-equality).
- **switchMap**: switch to latest inner observable; cancels stale async work (HTTP, route params).
- **takeUntil(notifier$)**: declarative disposal — complete when destroy signal fires.
- **map / filter**: pure stream transforms; no side effects inside operators.

## Composition idioms

- Component lifecycle: `source$.pipe(debounceTime(300), distinctUntilChanged(), switchMap(load), takeUntil(destroy$)).subscribe(...)`.
- State + events: `BehaviorSubject` for snapshot state; cold `fromEvent` or `Subject` for user actions.
- Derived state: `combineLatest([a$, b$]).pipe(map(([a, b]) => derive(a, b)))`.
- Disposal: store `Subscription`, call `unsubscribe()` in `ngOnDestroy` / effect cleanup / `finally`.

## Do / Don't

- **Do** mirror RxDart discipline: BehaviorSubject for state, bounded replay only, switchMap for network.
- **Do** use `takeUntil` or `Subscription` management for every `subscribe`.
- **Do** emit immutable snapshots from `map`; never mutate closed-over objects.
- **Don't** use unbounded `ReplaySubject` for general state — prefer `BehaviorSubject`.
- **Don't** nest subscriptions manually; compose with `switchMap`/`mergeMap` intentionally.
- **Don't** perform HTTP directly inside `map`; return observables from `switchMap` instead.
""",
}


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _libraries_from_pubspec(root: Path) -> tuple[str, ...]:
    content = _read_text(root / "pubspec.yaml")
    match content:
        case None:
            return ()
        case text:
            return tuple(sorted(set(_PUBSPEC_RE.findall(text))))


def _libraries_from_package_json(root: Path) -> tuple[str, ...]:
    content = _read_text(root / "package.json")
    match content:
        case None:
            return ()
        case text:
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                return ()
            deps = {
                *data.get("dependencies", {}).keys(),
                *data.get("devDependencies", {}).keys(),
            }
            return tuple(sorted(deps & _NODE_LIBRARIES))


def detect_libraries(root: Path) -> tuple[str, ...]:
    found = _libraries_from_pubspec(root) + _libraries_from_package_json(root)
    return tuple(sorted(set(found)))


def write_profiles(dest: Path, libraries: tuple[str, ...]) -> tuple[Path, ...]:
    knowledge_dir = dest / ".fp-enforcer" / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    return tuple(
        _write_profile(knowledge_dir, library_id)
        for library_id in libraries
        if library_id in PROFILES
    )


def _write_profile(knowledge_dir: Path, library_id: str) -> Path:
    path = knowledge_dir / f"{library_id}.md"
    path.write_text(PROFILES[library_id], encoding="utf-8")
    return path


def run(dest: Path) -> tuple[Path, ...]:
    return write_profiles(dest, detect_libraries(dest))
