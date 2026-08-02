"""Tests for fp_enforcer.validate."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fp_enforcer.core import Pattern, PatternPack, Violation
from fp_enforcer import validate


def _dart_pack() -> PatternPack:
    return PatternPack(
        language="dart",
        suffixes=(".dart",),
        exclude_suffixes=(".g.dart",),
        patterns=(
            Pattern(
                id="no-else",
                regex=r"\belse\b",
                message="avoid else blocks",
                rule="fp-core 8-9",
            ),
            Pattern(
                id="no-var",
                regex=r"\bvar\b",
                message="use final or const",
                rule="fp-core 12",
            ),
            Pattern(
                id="no-isLeft",
                regex=r"isLeft\(\)",
                message="use fold not isLeft",
                rule="fp-core 11",
            ),
            Pattern(
                id="no-Tuple",
                regex=r"Tuple2",
                message="no Tuple returns",
                rule="fp-core 14",
            ),
            Pattern(
                id="no-async-void",
                regex=r"async void",
                message="no async void",
                rule="fp-core 3",
            ),
            Pattern(
                id="no-try",
                regex=r"try\s*\{",
                message="no business try/catch",
                rule="fp-core 5",
            ),
        ),
    )


_SAMPLE_DART = """\
void main() {
  if (ready) {
    go();
  } else {
    stop();
  }
  var count = 0;
  if (result.isLeft()) {
    return;
  }
  final pair = Tuple2(a, b);
  async void broken() {}
  try {
    risky();
  } catch (e) {}
}
"""


class ValidateScanTextTests(unittest.TestCase):
    def test_scan_text_finds_expected_violations(self) -> None:
        pack = _dart_pack()
        violations = validate.scan_text(pack, _SAMPLE_DART, "lib/main.dart")
        by_id = {item.pattern_id: item.line for item in violations}
        self.assertEqual(by_id["no-else"], 4)
        self.assertEqual(by_id["no-var"], 7)
        self.assertEqual(by_id["no-isLeft"], 8)
        self.assertEqual(by_id["no-Tuple"], 11)
        self.assertEqual(by_id["no-async-void"], 12)
        self.assertEqual(by_id["no-try"], 13)

    def test_violations_ordered_by_line_then_pattern(self) -> None:
        pack = _dart_pack()
        text = "var a = 1;\nvar b = 2;\n"
        violations = validate.scan_text(pack, text, "a.dart")
        self.assertEqual(
            [item.line for item in violations],
            [1, 2],
        )


class PackForTests(unittest.TestCase):
    def test_excludes_generated_suffix(self) -> None:
        packs = (_dart_pack(),)
        self.assertIsNone(validate.pack_for(packs, "lib/foo.g.dart"))

    def test_matches_regular_dart_file(self) -> None:
        packs = (_dart_pack(),)
        matched = validate.pack_for(packs, "lib/foo.dart")
        self.assertIsNotNone(matched)
        self.assertEqual(matched.language, "dart")


class ScanDiffTests(unittest.TestCase):
    def test_scan_diff_added_lines_only_with_correct_line_numbers(self) -> None:
        packs = (_dart_pack(),)
        diff = "\n".join(
            [
                "--- a/lib/sample.dart",
                "+++ b/lib/sample.dart",
                "@@ -1,3 +1,4 @@",
                " unchanged",
                "-removed var old",
                "+added else here",
                " still context",
                "+var fresh",
            ]
        )
        violations = validate.scan_diff(packs, diff)
        by_id = {item.pattern_id: item for item in violations}
        self.assertEqual(by_id["no-else"].line, 2)
        self.assertEqual(by_id["no-else"].path, "lib/sample.dart")
        self.assertEqual(by_id["no-var"].line, 4)
        self.assertEqual(len(violations), 2)

    def test_scan_diff_skips_unmatched_paths(self) -> None:
        packs = (_dart_pack(),)
        diff = "\n".join(
            [
                "--- a/readme.md",
                "+++ b/readme.md",
                "@@ -0,0 +1,1 @@",
                "+else should not scan",
            ]
        )
        self.assertEqual(validate.scan_diff(packs, diff), ())


class FormatReportTests(unittest.TestCase):
    def test_format_report_exact_shape(self) -> None:
        violations = (
            Violation(
                path="lib/a.dart",
                line=3,
                pattern_id="no-else",
                message="avoid else blocks",
                rule="fp-core 8-9",
            ),
        )
        self.assertEqual(
            validate.format_report(violations),
            "lib/a.dart:3: [no-else] avoid else blocks (fp-core 8-9)",
        )


class LoadPacksTests(unittest.TestCase):
    def test_load_packs_from_tempdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            patterns_dir = Path(tmp)
            payload = {
                "language": "dart",
                "suffixes": [".dart"],
                "exclude_suffixes": [".g.dart"],
                "patterns": [
                    {
                        "id": "no-else",
                        "regex": r"\belse\b",
                        "message": "msg",
                        "rule": "fp-core 8-9",
                    }
                ],
            }
            (patterns_dir / "dart.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            packs = validate.load_packs(patterns_dir)
            self.assertEqual(len(packs), 1)
            self.assertEqual(packs[0].language, "dart")
            self.assertEqual(packs[0].patterns[0].id, "no-else")

    def test_invalid_regex_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            patterns_dir = Path(tmp)
            payload = {
                "language": "bad",
                "suffixes": [],
                "exclude_suffixes": [],
                "patterns": [
                    {
                        "id": "broken",
                        "regex": r"(?P<bad",
                        "message": "msg",
                        "rule": "rule",
                    }
                ],
            }
            (patterns_dir / "bad.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            with self.assertRaises(ValueError) as ctx:
                validate.load_packs(patterns_dir)
            message = str(ctx.exception)
            self.assertIn("bad", message)
            self.assertIn("broken", message)


if __name__ == "__main__":
    unittest.main()
