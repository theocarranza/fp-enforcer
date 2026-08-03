# Flutter: Pure Presentation

## Widget Purity

1. Widgets are pure containers — they present. Business logic and data fetching belong strictly in controllers, ViewModels, helper classes, or functions.
2. Refactor thresholds: build methods > 30 lines or widget classes > 100 lines must be decomposed.
3. Atomic components: small, single-purpose private `StatelessWidget` classes over helper methods returning widgets.
4. Avoid `StatefulWidget`, `ValueNotifier`, `ChangeNotifier`, and the like.

## State Management

1. Ephemeral UI state (animations, scroll controllers): `flutter_hooks`.
2. Shared business state: the project's chosen container (Provider / Riverpod / GetX) — logic stays functional inside it.
3. Render complex UI state by exhaustively switching over a sealed state ADT.
4. Give state classes value equality (`Equatable`, records, or sealed data classes) — reference comparison triggers spurious rebuilds.

## Performance

1. The 16ms frame budget covers all Dart execution: parsing and mapping jank comes from the data layer, not the widget tree. Offload heavy `.map().where().toList()..sort()` chains to `Isolate.run()`/`compute()`.
2. Startup: parallelize independent init with `Future.wait`; defer non-critical work with `addPostFrameCallback`; prefetch images concurrently.
3. Always `ListView.builder` for large datasets (`itemExtent` when height is fixed); cursor-based pagination with ~200–400px prefetch.
4. Heavy boolean getters short-circuit with `||`/`&&` instead of list processing (`.any`, `.reduce`).
