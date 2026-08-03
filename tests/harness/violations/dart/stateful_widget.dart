// Violates: fp-flutter widget purity 4 — StatefulWidget / ChangeNotifier.
// Expected: MISSED — no pattern exists.
import '../../stubs/flutter_stubs.g.dart';

class CounterPage extends StatefulWidget {
  const CounterPage({super.key});

  @override
  State<CounterPage> createState() => _CounterPageState();
}

class _CounterPageState extends State<CounterPage> {
  final ChangeNotifier notifier = ChangeNotifier();

  @override
  Widget build(BuildContext context) => const SizedBox();
}
