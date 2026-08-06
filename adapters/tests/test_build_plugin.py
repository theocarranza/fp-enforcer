#!/usr/bin/env python3
"""Packaging smoke tests for FP Enforcer host adapters."""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _build_lib import OVERLAY_SKILL, PLUGIN_NAME, Right, fold, inject_overlay, repo_root, run_build


class BuildPluginTests(unittest.TestCase):
    def test_inject_overlay_preserves_frontmatter(self) -> None:
        skill = "---\nname: fp-validate\ndescription: demo\nlicense: MIT\n---\n\nBody\n"
        result = inject_overlay(skill, "## Overlay\n\nInjected.")
        text = fold(result, self.fail, lambda value: value)
        self.assertTrue(text.startswith("---\nname: fp-validate\n"))
        self.assertIn("## Overlay", text)
        self.assertIn("Body", text)

    def test_build_cursor_ships_product_assets_without_mutating_canonical(self) -> None:
        root = repo_root()
        canonical = (root / "skills" / OVERLAY_SKILL / "SKILL.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "cursor-marketplace"
            zip_path = Path(temporary) / "plugin.zip"
            result = run_build(
                host="cursor",
                host_plugin_dir=".cursor-plugin",
                adapter_root=root / "adapters" / "cursor",
                output=output,
                zip_path=zip_path,
            )
            payload = fold(result, self.fail, lambda value: value)
            self.assertIsInstance(result, Right)
            plugin = output / "plugins" / PLUGIN_NAME
            built_skill = (plugin / "skills" / OVERLAY_SKILL / "SKILL.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("## Cursor adapter execution", built_skill)
            self.assertEqual(
                canonical,
                (root / "skills" / OVERLAY_SKILL / "SKILL.md").read_text(encoding="utf-8"),
            )
            for name in ("fp-validate", "fp-repair", "fp-learn", "fp-assimilate", "fp-wire"):
                self.assertTrue((plugin / "skills" / name / "SKILL.md").is_file())
            self.assertTrue((plugin / "fp_enforcer" / "__main__.py").is_file())
            self.assertTrue((plugin / "fp_enforcer" / "rules" / "manifest.json").is_file())
            self.assertTrue((plugin / "hooks" / "hooks.json").is_file())
            self.assertTrue((plugin / "assets" / "logo.png").is_file())
            self.assertFalse((plugin / "scripts" / "validate.sh").exists())
            self.assertFalse((plugin / "skills" / "hello").exists())
            self.assertTrue((output / "BUILD-MANIFEST.json").is_file())
            self.assertTrue(zip_path.is_file())
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
            self.assertTrue(any(name.startswith("cursor-marketplace/") for name in names))
            self.assertIsNotNone(payload["zip"])

    def test_build_codex_writes_agents_plugins_marketplace_manifest(self) -> None:
        root = repo_root()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "codex-marketplace"
            zip_path = Path(temporary) / "plugin.zip"
            result = run_build(
                host="codex",
                host_plugin_dir=".codex-plugin",
                adapter_root=root / "adapters" / "codex",
                output=output,
                zip_path=zip_path,
            )
            fold(result, self.fail, lambda value: value)
            agents_manifest = output / ".agents" / "plugins" / "marketplace.json"
            claude_manifest = output / ".claude-plugin" / "marketplace.json"
            vendor_manifest = output / ".codex-plugin" / "marketplace.json"
            self.assertTrue(agents_manifest.is_file())
            self.assertTrue(claude_manifest.is_file())
            self.assertTrue(vendor_manifest.is_file())
            self.assertEqual(agents_manifest.read_text(), claude_manifest.read_text())
            self.assertEqual(agents_manifest.read_text(), vendor_manifest.read_text())


if __name__ == "__main__":
    raise SystemExit(unittest.main())
