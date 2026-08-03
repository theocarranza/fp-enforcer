"""CLI exit-code contracts for validate, learn, and assimilate."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fp_enforcer.__main__ import main
from fp_enforcer.assimilate import AssimilateReport


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
