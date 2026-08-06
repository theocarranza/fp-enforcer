"""Regression: published wheels must ship fp_enforcer.adapters."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from setuptools.config.pyprojecttoml import apply_configuration
from setuptools.dist import Distribution

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _configured_packages(root: Path) -> frozenset[str]:
    dist = Distribution()
    apply_configuration(dist, str(root / "pyproject.toml"))
    return frozenset(dist.packages or ())


class PackagingTests(unittest.TestCase):
    def test_configured_packages_include_adapters(self) -> None:
        packages = _configured_packages(_PROJECT_ROOT)
        self.assertIn("fp_enforcer", packages)
        self.assertIn(
            "fp_enforcer.adapters",
            packages,
            "setuptools packages must include fp_enforcer.adapters "
            "or wire-vendored hooks fail with ModuleNotFoundError",
        )

    def test_built_wheel_includes_adapters(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            staging = Path(temp) / "src"
            dist = Path(temp) / "dist"
            shutil.copytree(
                _PROJECT_ROOT,
                staging,
                ignore=shutil.ignore_patterns(
                    ".git",
                    "__pycache__",
                    "*.egg-info",
                    ".fp-enforcer",
                    "dist",
                    "build",
                    ".venv",
                ),
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "build",
                    "--wheel",
                    "--outdir",
                    str(dist),
                ],
                cwd=staging,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                completed.returncode,
                0,
                completed.stdout + "\n" + completed.stderr,
            )
            wheels = tuple(dist.glob("*.whl"))
            self.assertEqual(len(wheels), 1)
            with zipfile.ZipFile(wheels[0]) as archive:
                names = frozenset(archive.namelist())
            for adapter in (
                "fp_enforcer/adapters/__init__.py",
                "fp_enforcer/adapters/antigravity.py",
                "fp_enforcer/adapters/claude.py",
                "fp_enforcer/adapters/codex.py",
                "fp_enforcer/adapters/cursor.py",
            ):
                self.assertIn(adapter, names)
            self.assertTrue(
                any(name.startswith("fp_enforcer/rules/") for name in names)
            )
            self.assertTrue(
                any(name.startswith("fp_enforcer/skills/") for name in names)
            )


if __name__ == "__main__":
    unittest.main()
