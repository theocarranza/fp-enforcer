"""Harness regression tests: fixtures pin scanner recall and precision.

violations/   every fixture must flag an exact set of pattern ids (recall)
clean/        rule-compliant code must produce zero violations (precision)
suppressions/ fp-allow directives must waive exactly the justified hits
stubs/        excluded via .g.dart suffix, must never be scanned
"""

from __future__ import annotations

import unittest
from pathlib import Path

from fp_enforcer import validate
from fp_enforcer.core import Violation

_HARNESS_DIR = Path(__file__).resolve().parent / "harness"

_EXPECTED_BY_FIXTURE: dict[str, frozenset[str]] = {
    "ambient_effect.ts": frozenset({"no-ambient-effect"}),
    "async_void.dart": frozenset({"no-async-void"}),
    "either_unwrap.dart": frozenset({"fold-not-unwrap"}),
    "else_branch.dart": frozenset({"no-else"}),
    "else_branch.ts": frozenset({"no-else"}),
    "for_loop.ts": frozenset({"no-let", "no-for-loop", "no-collection-mutation"}),
    "imperative_loop.dart": frozenset(
        {"no-for-loop", "no-collection-mutation", "no-var", "no-reassignment"}
    ),
    "let_binding.ts": frozenset({"no-let", "no-for-loop"}),
    "manual_listen.dart": frozenset({"no-manual-listen"}),
    "mutable_class.dart": frozenset({"no-mutable-field", "no-late"}),
    "mutation.dart": frozenset(
        {"no-mutable-field", "no-reassignment", "no-collection-mutation"}
    ),
    "mutation.ts": frozenset({"no-collection-mutation", "no-field-write"}),
    "non_null_assertion.ts": frozenset({"no-non-null-assertion"}),
    "or_fallback.ts": frozenset({"no-or-fallback"}),
    "replay_subject_unbounded.dart": frozenset({"no-unbounded-replay"}),
    "seedless_reduce.ts": frozenset({"no-seedless-reduce"}),
    "stateful_widget.dart": frozenset({"no-stateful-widget"}),
    "throw_domain.dart": frozenset({"no-throw-domain"}),
    "throw_internal.ts": frozenset({"no-throw-internal"}),
    "try_catch_usecase.dart": frozenset({"no-try-catch"}),
    "tuple_return.dart": frozenset({"no-tuple-return"}),
    "var_binding.ts": frozenset({"no-var"}),
    "var_usage.dart": frozenset({"no-var", "no-for-loop", "no-reassignment"}),
}


def _scan(relative: str) -> tuple[Violation, ...]:
    packs = validate.load_packs(validate.default_patterns_dir())
    return validate.scan_paths(packs, (_HARNESS_DIR / relative,))


class HarnessRecallTests(unittest.TestCase):
    def test_violation_fixtures_flag_exact_expected_patterns(self) -> None:
        by_fixture: dict[str, set[str]] = {}
        for item in _scan("violations"):
            by_fixture.setdefault(Path(item.path).name, set()).add(item.pattern_id)
        self.assertEqual(
            {name: frozenset(ids) for name, ids in by_fixture.items()},
            _EXPECTED_BY_FIXTURE,
        )


class HarnessPrecisionTests(unittest.TestCase):
    def test_clean_fixtures_produce_zero_violations(self) -> None:
        self.assertEqual(_scan("clean"), ())

    def test_suppression_fixtures_produce_zero_violations(self) -> None:
        self.assertEqual(_scan("suppressions"), ())

    def test_stub_files_are_never_scanned(self) -> None:
        self.assertEqual(_scan("stubs"), ())


if __name__ == "__main__":
    unittest.main()
