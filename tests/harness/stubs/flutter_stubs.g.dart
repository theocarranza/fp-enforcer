// Minimal flutter/material stand-ins so harness fixtures analyze without
// the Flutter SDK. Named .g.dart so the scanner excludes these declarations
// (ChangeNotifier/StatefulWidget would otherwise self-trigger patterns).
abstract class Widget {
  const Widget({this.key});

  final Object? key;
}

abstract class StatefulWidget extends Widget {
  const StatefulWidget({super.key});

  State<StatefulWidget> createState();
}

abstract class StatelessWidget extends Widget {
  const StatelessWidget({super.key});

  Widget build(BuildContext context);
}

abstract class State<T extends StatefulWidget> {
  Widget build(BuildContext context);
}

final class BuildContext {
  const BuildContext();
}

final class SizedBox extends Widget {
  const SizedBox({super.key});
}

class ChangeNotifier {}

class ValueNotifier<T> {
  ValueNotifier(this.value);

  T value;
}
