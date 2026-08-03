// Justified suppression: the disposal binding mandated by fp-rxdart memory 1
// trips no-collection-mutation by design. Expected: NO violations reported.
final class DisposalBag {
  final List<Object> _subscriptions = <Object>[];

  void bind(Object subscription) {
    // fp-allow: no-collection-mutation — disposal binding, fp-rxdart memory 1
    _subscriptions.add(subscription);
  }
}
