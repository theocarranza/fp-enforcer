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


class CommentStrippingTests(unittest.TestCase):
    def test_trailing_comment_not_scanned(self) -> None:
        pack = _dart_pack()
        text = "final ok = 1; // else var isLeft()\n"
        self.assertEqual(validate.scan_text(pack, text, "a.dart"), ())

    def test_block_comment_spanning_lines_not_scanned(self) -> None:
        pack = _dart_pack()
        text = "/*\nelse var\n*/\nfinal ok = 1;\n"
        self.assertEqual(validate.scan_text(pack, text, "a.dart"), ())

    def test_inline_block_comment_removed_but_code_kept(self) -> None:
        pack = _dart_pack()
        text = "final ok = /* else */ 1;\nvar count = 0;\n"
        violations = validate.scan_text(pack, text, "a.dart")
        self.assertEqual([item.pattern_id for item in violations], ["no-var"])

    def test_url_string_does_not_hide_code(self) -> None:
        pack = _dart_pack()
        text = "final u = 'https://x.dev';\nvar count = 0;\n"
        violations = validate.scan_text(pack, text, "a.dart")
        self.assertEqual([item.pattern_id for item in violations], ["no-var"])


class SuppressionTests(unittest.TestCase):
    def test_fp_allow_suppresses_named_pattern(self) -> None:
        pack = _dart_pack()
        text = "var count = 0; // fp-allow: no-var\n"
        self.assertEqual(validate.scan_text(pack, text, "a.dart"), ())

    def test_fp_allow_does_not_suppress_other_patterns(self) -> None:
        pack = _dart_pack()
        text = "var count = 0; // fp-allow: no-else\n"
        violations = validate.scan_text(pack, text, "a.dart")
        self.assertEqual([item.pattern_id for item in violations], ["no-var"])

    def test_fp_allow_comma_separated(self) -> None:
        pack = _dart_pack()
        text = "} else { var count = 0; } // fp-allow: no-else, no-var\n"
        self.assertEqual(validate.scan_text(pack, text, "a.dart"), ())

    def test_fp_allow_on_preceding_comment_line(self) -> None:
        pack = _dart_pack()
        text = "// fp-allow: no-var — justified\nvar count = 0;\nvar other = 1;\n"
        violations = validate.scan_text(pack, text, "a.dart")
        self.assertEqual([item.line for item in violations], [3])

    def test_fp_allow_applies_in_diffs(self) -> None:
        packs = (_dart_pack(),)
        diff = "\n".join(
            [
                "--- a/lib/sample.dart",
                "+++ b/lib/sample.dart",
                "@@ -0,0 +1,1 @@",
                "+var count = 0; // fp-allow: no-var",
            ]
        )
        self.assertEqual(validate.scan_diff(packs, diff), ())


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


def _dart_extension_pack() -> PatternPack:
    return PatternPack(
        language="dart",
        suffixes=(".dart",),
        exclude_suffixes=(),
        patterns=(
            Pattern(
                id="no-dynamic",
                regex=r"\bdynamic\b",
                message="no dynamic",
                rule="fp-dart-style 1",
            ),
        ),
    )


class PacksForTests(unittest.TestCase):
    def test_packs_for_returns_all_matching(self) -> None:
        packs = (_dart_pack(), _dart_extension_pack())
        self.assertEqual(len(validate.packs_for(packs, "lib/a.dart")), 2)

    def test_packs_for_respects_each_pack_exclusions(self) -> None:
        packs = (_dart_pack(), _dart_extension_pack())
        self.assertEqual(len(validate.packs_for(packs, "lib/a.g.dart")), 1)

    def test_packs_for_no_match_returns_empty(self) -> None:
        packs = (_dart_pack(), _dart_extension_pack())
        self.assertEqual(validate.packs_for(packs, "lib/a.md"), ())

    def test_pack_for_still_returns_first_match(self) -> None:
        packs = (_dart_pack(), _dart_extension_pack())
        matched = validate.pack_for(packs, "lib/a.dart")
        self.assertIsNotNone(matched)
        self.assertEqual(matched.language, "dart")


class MultiPackScanTests(unittest.TestCase):
    def test_scan_file_reports_from_all_matching_packs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sample.dart"
            target.write_text("dynamic x = 1;\n", encoding="utf-8")
            packs = (_dart_pack(), _dart_extension_pack())
            violations = validate.scan_file(packs, target)
            self.assertEqual(
                {item.pattern_id for item in violations}, {"no-dynamic"}
            )

    def test_identical_violations_across_packs_deduped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sample.dart"
            target.write_text("dynamic x = 1;\n", encoding="utf-8")
            packs = (_dart_extension_pack(), _dart_extension_pack())
            violations = validate.scan_file(packs, target)
            self.assertEqual(len(violations), 1)

    def test_scan_diff_reports_from_all_matching_packs(self) -> None:
        packs = (_dart_pack(), _dart_extension_pack())
        diff = "\n".join(
            [
                "--- a/lib/sample.dart",
                "+++ b/lib/sample.dart",
                "@@ -0,0 +1,1 @@",
                "+dynamic count = 0; // fp-allow: nothing",
            ]
        )
        violations = validate.scan_diff(packs, diff)
        self.assertEqual(
            {item.pattern_id for item in violations}, {"no-dynamic"}
        )

    def test_load_packs_includes_learned_subdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            patterns_dir = Path(tmp)
            learned_dir = patterns_dir / "learned"
            learned_dir.mkdir()
            payload = {
                "language": "dart",
                "suffixes": [".dart"],
                "exclude_suffixes": [],
                "patterns": [
                    {"id": "p", "regex": "x", "message": "m", "rule": "r"}
                ],
            }
            (patterns_dir / "dart.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            (learned_dir / "extra.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            packs = validate.load_packs(patterns_dir)
            self.assertEqual(len(packs), 2)

    def test_load_pack_reads_single_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dart.json"
            payload = {
                "language": "dart",
                "suffixes": [".dart"],
                "exclude_suffixes": [],
                "patterns": [
                    {"id": "p", "regex": "x", "message": "m", "rule": "r"}
                ],
                "self_test": {"violations": [], "clean": []},
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            pack = validate.load_pack(path)
            self.assertEqual(pack.language, "dart")
            self.assertEqual(pack.patterns[0].id, "p")


if __name__ == "__main__":
    unittest.main()
