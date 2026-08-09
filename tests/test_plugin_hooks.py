"""Plugin-level hooks/hooks.json schema guards (mirrors scripts/validate.sh)."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS_PATH = ROOT / "hooks" / "hooks.json"
ALLOWED_KEYS = frozenset({"description", "hooks"})


def plugin_hooks_error(document: object) -> str | None:
    match document:
        case dict() as plugin_hooks:
            pass
        case other:
            return f"hooks/hooks.json must be a JSON object, got {type(other).__name__}"

    extra = sorted(set(plugin_hooks) - ALLOWED_KEYS)
    match extra:
        case []:
            pass
        case keys:
            return f"hooks/hooks.json has unsupported top-level keys: {', '.join(keys)}"

    match plugin_hooks.get("hooks"):
        case hooks if isinstance(hooks, dict) and hooks == {}:
            return None
        case hooks if isinstance(hooks, dict):
            return (
                "hooks/hooks.json hooks must be empty at plugin level; use fp-enforcer wire"
            )
        case other:
            return f"hooks/hooks.json hooks must be an empty object, got {other!r}"


class PluginHooksSchemaTests(unittest.TestCase):
    def test_shipped_hooks_json_is_valid(self) -> None:
        document = json.loads(HOOKS_PATH.read_text(encoding="utf-8"))
        self.assertIsNone(plugin_hooks_error(document))

    def test_version_key_rejected(self) -> None:
        error = plugin_hooks_error({"version": 1, "description": "demo", "hooks": {}})
        self.assertIsNotNone(error)
        self.assertIn("unsupported top-level keys", error)
        self.assertIn("version", error)

    def test_missing_hooks_rejected(self) -> None:
        error = plugin_hooks_error({"description": "demo"})
        self.assertIsNotNone(error)
        self.assertIn("hooks must be an empty object", error)

    def test_non_empty_hooks_rejected(self) -> None:
        error = plugin_hooks_error({"hooks": {"stop": []}})
        self.assertIsNotNone(error)
        self.assertIn("must be empty", error)

    def test_validate_sh_passes(self) -> None:
        result = subprocess.run(
            ["bash", "scripts/validate.sh"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
