// Compliant: exhaustive switch expression, no else (fp-core 8-10).
// Expected: NO violations reported.
String classify(int score) => switch (score) {
      > 90 => 'gold',
      > 50 => 'silver',
      _ => 'bronze',
    };
