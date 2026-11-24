"""CLI exit-code contracts for validate, learn, and assimilate."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fp_enforcer.__main__ import main
from fp_enforcer.assimilate import AssimilateReport
from tests.test_hook_runtime import _commit, _edit, _reason, _workspace, _write


class ValidateCliTests(unittest.TestCase):
    def test_clean_path_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clean.ts"
            path.write_text("const value = 1;\n", encoding="utf-8")
            self.assertEqual(main(["validate", str(path)]), 0)

    def test_violation_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.ts"
            path.write_text("let value = 1;\n", encoding="utf-8")
            self.assertEqual(main(["validate", str(path)]), 1)


def _run_cli(argv: list[str]) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(argv)
    return code, buffer.getvalue()


class ScanLegacyCliTests(unittest.TestCase):
    def test_clean_file_exits_zero_and_prints_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clean.ts"
            path.write_text("const value = 1;\n", encoding="utf-8")
            self.assertEqual(_run_cli(["scan-legacy", str(path)]), (0, ""))

    def test_violation_reports_path_line_and_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.ts"
            path.write_text("let value = 1;\n", encoding="utf-8")
            code, output = _run_cli(["scan-legacy", str(path)])
            self.assertEqual(code, 1)
            self.assertIn(f"{path}:1: [no-let]", output)

    def test_directory_is_walked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "bad.ts").write_text("let value = 1;\n", encoding="utf-8")
            code, output = _run_cli(["scan-legacy", tmp])
            self.assertEqual(code, 1)
            self.assertIn("bad.ts:1: [no-let]", output)

    def test_reports_whole_file_while_edit_hook_reports_only_changes(self) -> None:
        with _workspace() as repo:
            _commit(repo, {"a.ts": "let legacy = 1;\n"}, "base")
            _write(repo, "a.ts", "let legacy = 1;\nlet fresh = 2;\n")
            code, output = _run_cli(["scan-legacy", "a.ts"])
            self.assertEqual(code, 1)
            self.assertIn("a.ts:1: [no-let]", output)
            self.assertIn("a.ts:2: [no-let]", output)
            reason = _reason(_edit(repo / "a.ts"))
            self.assertIn("a.ts:2: [no-let]", reason)
            self.assertNotIn("a.ts:1: [no-let]", reason)

    def test_patterns_dir_is_honoured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packs = root / "packs"
            packs.mkdir()
            (packs / "zzz.json").write_text(
                json.dumps(
                    {
                        "language": "zzz",
                        "suffixes": [".zzz"],
                        "exclude_suffixes": [],
                        "patterns": [
                            {
                                "id": "no-bang",
                                "regex": "BANG",
                                "message": "no bang",
                                "rule": "test 1",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            target = root / "a.zzz"
            target.write_text("BANG\n", encoding="utf-8")
            code, output = _run_cli(
                ["scan-legacy", "--patterns-dir", str(packs), str(target)]
            )
            self.assertEqual(code, 1)
            self.assertIn("[no-bang]", output)
            self.assertEqual(_run_cli(["scan-legacy", str(target)]), (0, ""))


class ValidateDiffCliTests(unittest.TestCase):
    def test_validate_diff_reports_only_added_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            diff = Path(tmp) / "change.diff"
            diff.write_text(
                "\n".join(
                    [
                        "--- a/lib/a.ts",
                        "+++ b/lib/a.ts",
                        "@@ -1,1 +1,2 @@",
                        " let legacy = 1;",
                        "+let added = 1;",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            code, output = _run_cli(["validate", "--diff", str(diff)])
            self.assertEqual(code, 1)
            self.assertIn("lib/a.ts:2: [no-let]", output)
            self.assertNotIn("lib/a.ts:1: [no-let]", output)


class HooksNeverScanLegacyTests(unittest.TestCase):
    def test_no_hook_or_adapter_calls_scan_legacy(self) -> None:
        root = Path(__file__).resolve().parent.parent
        sources = (
            (root / "fp_enforcer" / "hook_runtime.py",)
            + tuple(path for path in (root / "hooks").rglob("*") if path.is_file())
            + tuple((root / "fp_enforcer" / "adapters").glob("*.py"))
        )
        for source in sources:
            text = source.read_text(encoding="utf-8", errors="replace")
            with self.subTest(source=str(source)):
                self.assertNotIn("scan-legacy", text)
                self.assertNotIn("scan_legacy", text)


class LearnCliTests(unittest.TestCase):
    def test_learn_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(
                json.dumps({"dependencies": {"rxjs": "^7.0.0"}}),
                encoding="utf-8",
            )
            self.assertEqual(main(["learn", "--dest", str(root)]), 0)


class AssimilateCliTests(unittest.TestCase):
    def test_successful_activation_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pubspec.yaml").write_text(
                "name: app\nenvironment:\n  sdk: ^3.4.0\n", encoding="utf-8"
            )
            self.assertEqual(main(["assimilate", "--dest", str(root)]), 0)

    def test_gate_failure_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = AssimilateReport(
                activated=(),
                gate_failures=("dart3: no self_test",),
            )
            with patch("fp_enforcer.__main__.assimilate.run", return_value=report):
                self.assertEqual(main(["assimilate", "--dest", tmp]), 1)


if __name__ == "__main__":
    unittest.main()
