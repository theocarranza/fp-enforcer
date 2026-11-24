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


class ChangedLinesTests(unittest.TestCase):
    def test_hunk_with_count_yields_range(self) -> None:
        diff = "\n".join(
            [
                "+++ b/lib/a.dart",
                "@@ -3,2 +5,3 @@",
            ]
        )
        self.assertEqual(
            dict(validate.changed_lines(diff)),
            {"lib/a.dart": frozenset({5, 6, 7})},
        )

    def test_hunk_without_count_yields_single_line(self) -> None:
        diff = "\n".join(
            [
                "+++ b/lib/a.dart",
                "@@ -3 +5 @@",
            ]
        )
        self.assertEqual(
            dict(validate.changed_lines(diff)),
            {"lib/a.dart": frozenset({5})},
        )

    def test_pure_deletion_hunk_adds_no_lines(self) -> None:
        diff = "\n".join(
            [
                "+++ b/lib/a.dart",
                "@@ -4,2 +3,0 @@",
            ]
        )
        self.assertEqual(
            dict(validate.changed_lines(diff)),
            {"lib/a.dart": frozenset()},
        )

    def test_multiple_hunks_in_one_file_are_unioned(self) -> None:
        diff = "\n".join(
            [
                "+++ b/lib/a.dart",
                "@@ -2,2 +2,2 @@ a",
                "@@ -6,0 +7,2 @@ f",
            ]
        )
        self.assertEqual(
            dict(validate.changed_lines(diff)),
            {"lib/a.dart": frozenset({2, 3, 7, 8})},
        )

    def test_multiple_files_and_new_file(self) -> None:
        diff = "\n".join(
            [
                "--- a/lib/gone.dart",
                "+++ /dev/null",
                "@@ -1 +0,0 @@",
                "-x",
                "--- /dev/null",
                "+++ b/lib/new.dart",
                "@@ -0,0 +1,3 @@",
                "--- a/lib/old.dart",
                "+++ b/lib/old.dart",
                "@@ -10 +10,2 @@",
            ]
        )
        self.assertEqual(
            dict(validate.changed_lines(diff)),
            {
                "lib/new.dart": frozenset({1, 2, 3}),
                "lib/old.dart": frozenset({10, 11}),
            },
        )

    def test_deleted_file_has_no_entry(self) -> None:
        diff = "\n".join(
            [
                "+++ /dev/null",
                "@@ -1,4 +0,0 @@",
                "-a",
            ]
        )
        self.assertEqual(dict(validate.changed_lines(diff)), {})

    def test_trailing_tab_after_path_is_stripped(self) -> None:
        diff = "+++ b/lib/spaced name.dart\t\n@@ -1 +2 @@\n"
        self.assertEqual(
            dict(validate.changed_lines(diff)),
            {"lib/spaced name.dart": frozenset({2})},
        )

    def test_added_line_starting_with_plus_plus_is_not_a_header(self) -> None:
        diff = "\n".join(
            [
                "+++ b/lib/a.dart",
                "@@ -1,0 +2 @@",
                "+++ b/lib/fake.dart",
            ]
        )
        self.assertEqual(
            dict(validate.changed_lines(diff)),
            {"lib/a.dart": frozenset({2})},
        )

    def test_empty_input_gives_empty_mapping(self) -> None:
        self.assertEqual(dict(validate.changed_lines("")), {})

    def test_real_git_zero_context_diff(self) -> None:
        diff = "\n".join(
            [
                "diff --git a/added.dart b/added.dart",
                "new file mode 100644",
                "index 0000000..14883d4",
                "--- /dev/null",
                "+++ b/added.dart",
                "@@ -0,0 +1,3 @@",
                "+fresh1",
                "+fresh2",
                "+fresh3",
                "diff --git a/gone.dart b/gone.dart",
                "deleted file mode 100644",
                "index 587be6b..0000000",
                "--- a/gone.dart",
                "+++ /dev/null",
                "@@ -1 +0,0 @@",
                "-x",
                "diff --git a/lib.dart b/lib.dart",
                "index 0fdf397..d082662 100644",
                "--- a/lib.dart",
                "+++ b/lib.dart",
                "@@ -2,2 +2,2 @@ a",
                "-b",
                "-c",
                "+B",
                "+C",
                "@@ -6,0 +7,2 @@ f",
                "+new1",
                "+new2",
                "diff --git a/spaced name.dart b/spaced name.dart",
                "index 2fa992c..5975685 100644",
                "--- a/spaced name.dart\t",
                "+++ b/spaced name.dart\t",
                "@@ -1,0 +2 @@ keep",
                "+changed",
                "",
            ]
        )
        self.assertEqual(
            dict(validate.changed_lines(diff)),
            {
                "added.dart": frozenset({1, 2, 3}),
                "lib.dart": frozenset({2, 3, 7, 8}),
                "spaced name.dart": frozenset({2}),
            },
        )


class FilterViolationsTests(unittest.TestCase):
    def _violation(self, line: int, pattern_id: str) -> Violation:
        return Violation(
            path="lib/a.dart",
            line=line,
            pattern_id=pattern_id,
            message="m",
            rule="r",
        )

    def test_keeps_only_matching_lines_in_order(self) -> None:
        violations = (
            self._violation(5, "no-var"),
            self._violation(1, "no-else"),
            self._violation(7, "no-try"),
            self._violation(2, "no-var"),
        )
        kept = validate.filter_violations(violations, frozenset({2, 5}))
        self.assertEqual(
            [(item.line, item.pattern_id) for item in kept],
            [(5, "no-var"), (2, "no-var")],
        )

    def test_empty_line_set_keeps_nothing(self) -> None:
        violations = (self._violation(1, "no-var"),)
        self.assertEqual(validate.filter_violations(violations, frozenset()), ())


if __name__ == "__main__":
    unittest.main()
