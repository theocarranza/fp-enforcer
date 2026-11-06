"""The library-agnostic TypeScript knowledge must ship, run, and obey its own rules."""

from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

from fp_enforcer import validate

RULES = Path(__file__).resolve().parent.parent / "fp_enforcer" / "rules"
EXAMPLES = RULES / "examples" / "typescript"
LIBRARIES = RULES / "libraries"
_REF = re.compile(r"`((?:examples|libraries)/[\w/.-]+\.ts)`")


def _node_supports_type_stripping() -> bool:
    match shutil.which("node"):
        case None:
            return False
        case node:
            version = subprocess.run(
                [node, "--version"], capture_output=True, text=True, check=False
            ).stdout.strip().lstrip("v")
            major, minor = (int(part) for part in version.split(".")[:2])
            return (major, minor) >= (22, 6)


class TypeScriptKnowledgeTests(unittest.TestCase):
    def test_rule_references_resolve(self) -> None:
        text = (RULES / "fp-typescript.md").read_text(encoding="utf-8")
        refs = frozenset(_REF.findall(text))
        self.assertTrue(refs, "fp-typescript.md must cite runnable examples")
        missing = sorted(ref for ref in refs if not (RULES / ref).is_file())
        self.assertEqual(missing, [])

    def test_core_rule_has_algebra_section(self) -> None:
        text = (RULES / "fp-core.md").read_text(encoding="utf-8")
        self.assertIn("## Algebra", text)
        for term in ("associative", "identity", "first", "last", "applicative"):
            self.assertIn(term, text)

    def test_examples_obey_fp_enforcer(self) -> None:
        packs = validate.load_packs(validate.default_patterns_dir())
        violations = validate.scan_paths(packs, (EXAMPLES, LIBRARIES))
        self.assertEqual(validate.format_report(violations), "")

    @unittest.skipUnless(_node_supports_type_stripping(), "needs node >= 22.6")
    def test_agnostic_examples_run(self) -> None:
        examples = sorted(EXAMPLES.glob("*.ts"))
        self.assertGreaterEqual(len(examples), 3)
        for example in examples:
            with self.subTest(example=example.name):
                result = subprocess.run(
                    ["node", "--no-warnings", str(example)],
                    capture_output=True,
                    text=True,
                    stdin=subprocess.DEVNULL,
                    timeout=60,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
