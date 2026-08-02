"""Tests for fp_enforcer.learn."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fp_enforcer import learn


class DetectLibrariesTests(unittest.TestCase):
    def test_detect_libraries_from_pubspec_and_package_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pubspec.yaml").write_text(
                "\n".join(
                    [
                        "name: demo",
                        "dependencies:",
                        "  dartz: ^0.10.1",
                        "  rxdart: ^0.28.0",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "package.json").write_text(
                json.dumps(
                    {
                        "dependencies": {"fp-ts": "^2.16.0"},
                        "devDependencies": {"lodash": "^4.0.0"},
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                learn.detect_libraries(root),
                ("dartz", "fp-ts", "rxdart"),
            )


class WriteProfilesTests(unittest.TestCase):
    def test_write_profiles_creates_known_files_and_skips_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            written = learn.write_profiles(
                dest,
                ("dartz", "unknown-lib", "fp-ts"),
            )
            self.assertEqual(len(written), 2)
            knowledge = dest / ".fp-enforcer" / "knowledge"
            self.assertTrue((knowledge / "dartz.md").is_file())
            self.assertTrue((knowledge / "fp-ts.md").is_file())
            self.assertFalse((knowledge / "unknown-lib.md").exists())
            for path in written:
                self.assertTrue(path.read_text(encoding="utf-8").startswith("#"))

    def test_run_delegates_to_detect_and_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pubspec.yaml").write_text(
                "dependencies:\n  fpdart: ^1.0.0\n",
                encoding="utf-8",
            )
            paths = learn.run(root)
            self.assertEqual(len(paths), 1)
            self.assertEqual(paths[0].name, "fpdart.md")


if __name__ == "__main__":
    unittest.main()
