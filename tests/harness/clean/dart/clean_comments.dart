// Compliant: comments and strings may mention else, var, throw, listen,
// and sort freely; scanning must ignore them.
// Expected: NO violations reported.
/*
 * A block comment can say var, else, throw, ReplaySubject<String>(),
 * and even extends StatefulWidget across several lines.
 */
const url = 'https://example.com//docs'; // trailing comment: var else
const label = "don't mutate, use ?? not ||";
const raw = r'C:\temp\\path';
