"""Tests for fp_enforcer.assimilate."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fp_enforcer import assimilate


class DetectLanguageFeaturesTests(unittest.TestCase):
    def test_dart3_detected_from_sdk_constraint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pubspec.yaml").write_text(
                "name: app\nenvironment:\n  sdk: ^3.4.0\n", encoding="utf-8"
            )
            self.assertEqual(assimilate.detect_language_features(root), ("dart3",))

    def test_dart2_yields_no_features(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pubspec.yaml").write_text(
                "name: app\nenvironment:\n  sdk: ^2.19.0\n", encoding="utf-8"
            )
            self.assertEqual(assimilate.detect_language_features(root), ())

    def test_dart3_detected_from_range_sdk_constraint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pubspec.yaml").write_text(
                'name: app\nenvironment:\n  sdk: ">=3.0.0 <4.0.0"\n',
                encoding="utf-8",
            )
            self.assertEqual(assimilate.detect_language_features(root), ("dart3",))

    def test_dart2_range_sdk_constraint_yields_no_features(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pubspec.yaml").write_text(
                "name: app\nenvironment:\n  sdk: '>=2.19.0 <3.0.0'\n",
                encoding="utf-8",
            )
            self.assertEqual(assimilate.detect_language_features(root), ())

    def test_missing_pubspec_yields_no_features(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(assimilate.detect_language_features(Path(tmp)), ())


class SelectPacksTests(unittest.TestCase):
    def test_selects_only_detected_ids(self) -> None:
        selected = assimilate.select_packs(assimilate.SOURCE_ROOT, ("rxjs",))
        self.assertEqual([path.stem for path in selected], ["rxjs"])

    def test_unknown_ids_select_nothing(self) -> None:
        self.assertEqual(
            assimilate.select_packs(assimilate.SOURCE_ROOT, ("cobol",)), ()
        )


class RunTests(unittest.TestCase):
    def test_run_activates_packs_for_detected_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pubspec.yaml").write_text(
                "name: app\nenvironment:\n  sdk: ^3.4.0\n"
                "dependencies:\n  rxdart: ^0.28.0\n",
                encoding="utf-8",
            )
            (root / "package.json").write_text(
                json.dumps({"dependencies": {"rxjs": "^7.0.0"}}),
                encoding="utf-8",
            )
            report = assimilate.run(root)
            self.assertEqual(report.gate_failures, ())
            self.assertEqual(
                sorted(item.pack_id for item in report.activated),
                ["dart3", "rxjs"],
            )
            learned_dir = root / ".fp-enforcer" / "rules" / "patterns" / "learned"
            for item in report.activated:
                self.assertTrue(item.path.is_file())
                self.assertEqual(item.path.parent, learned_dir)

    def test_run_with_no_libraries_activates_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = assimilate.run(Path(tmp))
            self.assertEqual(report.activated, ())
            self.assertEqual(report.gate_failures, ())

    def test_malformed_curated_pack_fails_gate_without_blocking_others(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "src"
            library_dir = source / "rules" / "patterns" / "libraries"
            library_dir.mkdir(parents=True)
            (library_dir / "dart3.json").write_text(
                '{"feature": "dart3", "language": "dart",', encoding="utf-8"
            )
            (library_dir / "rxjs.json").write_text(
                (assimilate.SOURCE_ROOT / "rules/patterns/libraries/rxjs.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            dest = Path(tmp) / "dest"
            dest.mkdir()
            (dest / "pubspec.yaml").write_text(
                "name: app\nenvironment:\n  sdk: ^3.4.0\n", encoding="utf-8"
            )
            (dest / "package.json").write_text(
                json.dumps({"dependencies": {"rxjs": "^7.0.0"}}),
                encoding="utf-8",
            )
            report = assimilate.run(dest, source_root=source)
            self.assertEqual(len(report.gate_failures), 1)
            self.assertIn("dart3", report.gate_failures[0])
            self.assertEqual([item.pack_id for item in report.activated], ["rxjs"])

    def test_non_object_curated_pack_fails_gate_without_blocking_others(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "src"
            library_dir = source / "rules" / "patterns" / "libraries"
            library_dir.mkdir(parents=True)
            (library_dir / "dart3.json").write_text("[]", encoding="utf-8")
            (library_dir / "rxjs.json").write_text(
                (assimilate.SOURCE_ROOT / "rules/patterns/libraries/rxjs.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            dest = Path(tmp) / "dest"
            dest.mkdir()
            (dest / "pubspec.yaml").write_text(
                "name: app\nenvironment:\n  sdk: ^3.4.0\n", encoding="utf-8"
            )
            (dest / "package.json").write_text(
                json.dumps({"dependencies": {"rxjs": "^7.0.0"}}),
                encoding="utf-8",
            )
            report = assimilate.run(dest, source_root=source)
            self.assertEqual(len(report.gate_failures), 1)
            self.assertIn("dart3", report.gate_failures[0])
            self.assertIn("malformed pack JSON", report.gate_failures[0])
            self.assertEqual([item.pack_id for item in report.activated], ["rxjs"])

    def test_gate_failure_blocks_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "src"
            library_dir = source / "rules" / "patterns" / "libraries"
            library_dir.mkdir(parents=True)
            payload = {
                "feature": "dart3",
                "language": "dart",
                "suffixes": [".dart"],
                "exclude_suffixes": [],
                "patterns": [
                    {
                        "id": "no-foo",
                        "regex": "\\bfoo\\b",
                        "message": "m",
                        "rule": "r",
                    }
                ],
                "self_test": {"violations": ["bar();"], "clean": []},
            }
            (library_dir / "dart3.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            dest = Path(tmp) / "dest"
            dest.mkdir()
            (dest / "pubspec.yaml").write_text(
                "name: app\nenvironment:\n  sdk: ^3.4.0\n", encoding="utf-8"
            )
            report = assimilate.run(dest, source_root=source)
            self.assertEqual(report.activated, ())
            self.assertEqual(len(report.gate_failures), 1)
            self.assertIn("dart3", report.gate_failures[0])


class CuratedPackTests(unittest.TestCase):
    def test_every_curated_pack_passes_its_self_test(self) -> None:
        failures = tuple(
            failure
            for path in assimilate.curated_pack_paths(assimilate.SOURCE_ROOT)
            for failure in assimilate.pack_self_test_failures(path)
        )
        self.assertEqual(failures, ())
