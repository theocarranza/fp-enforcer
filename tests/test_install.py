"""Tests for fp-enforcer install/uninstall and hook runtime."""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fp_enforcer.hook_runtime import main
from fp_enforcer.install import SOURCE_ROOT, install, uninstall

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _build_fixture_source_root(base: Path) -> Path:
    # source_root is the package directory itself; rules/ and skills/
    # live inside it since the package-data relocation.
    fixture = base / "fixture-source" / "fp_enforcer"
    shutil.copytree(_PROJECT_ROOT / "fp_enforcer", fixture)
    skills = fixture / "skills" / "fp-enforcer"
    skills.mkdir(parents=True, exist_ok=True)
    (skills / "SKILL.md").write_text("# fp-enforcer\n", encoding="utf-8")
    return fixture


def _cursor_hook_commands(hooks_path: Path) -> tuple[str, ...]:
    document = json.loads(hooks_path.read_text(encoding="utf-8"))
    return tuple(
        entry.get("command", "")
        for entry in document.get("hooks", {}).get("postToolUse", [])
        + document.get("hooks", {}).get("stop", [])
    )


class InstallTests(unittest.TestCase):
    def test_install_preserves_foreign_cursor_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            hooks_path = dest / ".cursor" / "hooks.json"
            hooks_path.parent.mkdir(parents=True)
            hooks_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "hooks": {
                            "preToolUse": [
                                {
                                    "command": "echo foreign",
                                    "matcher": "Shell",
                                    "timeout": 5,
                                }
                            ]
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            fixture = _build_fixture_source_root(dest)
            install(dest, ("cursor",), source_root=fixture)

            document = json.loads(hooks_path.read_text(encoding="utf-8"))
            pre = document["hooks"]["preToolUse"]
            self.assertEqual(len(pre), 1)
            self.assertEqual(pre[0]["command"], "echo foreign")
            self.assertEqual(document["version"], 1)

            commands = _cursor_hook_commands(hooks_path)
            self.assertEqual(
                sum(".fp-enforcer/run_hook.py" in command for command in commands),
                2,
            )

    def test_install_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            fixture = _build_fixture_source_root(dest)
            install(dest, ("cursor",), source_root=fixture)
            install(dest, ("cursor",), source_root=fixture)

            hooks_path = dest / ".cursor" / "hooks.json"
            commands = _cursor_hook_commands(hooks_path)
            edit_commands = [
                command
                for command in commands
                if "--event edit" in command
            ]
            stop_commands = [
                command
                for command in commands
                if "--event stop" in command
            ]
            self.assertEqual(len(edit_commands), 1)
            self.assertEqual(len(stop_commands), 1)

    def test_cursor_rules_have_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            fixture = _build_fixture_source_root(dest)
            install(dest, ("cursor",), source_root=fixture)

            rule_files = list((dest / ".cursor" / "rules").glob("*.mdc"))
            self.assertTrue(rule_files)
            for rule_file in rule_files:
                text = rule_file.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"))
                self.assertIn("description:", text)
                self.assertIn("alwaysApply:", text)

    def test_uninstall_removes_fp_enforcer_but_keeps_foreign_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            hooks_path = dest / ".cursor" / "hooks.json"
            hooks_path.parent.mkdir(parents=True)
            hooks_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "hooks": {
                            "preToolUse": [
                                {
                                    "command": "echo foreign",
                                    "matcher": "Shell",
                                    "timeout": 5,
                                }
                            ]
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            fixture = _build_fixture_source_root(dest)
            install(dest, ("cursor",), source_root=fixture)
            uninstall(dest)

            self.assertFalse((dest / ".fp-enforcer").exists())
            self.assertFalse((dest / ".cursor" / "rules").exists())
            self.assertTrue((dest / ".cursor").is_dir())
            document = json.loads(hooks_path.read_text(encoding="utf-8"))
            self.assertIn("preToolUse", document["hooks"])
            self.assertEqual(document["hooks"]["preToolUse"][0]["command"], "echo foreign")
            self.assertFalse(
                any(
                    ".fp-enforcer/run_hook.py" in command
                    for command in _cursor_hook_commands(hooks_path)
                )
            )


@unittest.skipUnless(
    (_PROJECT_ROOT / "fp_enforcer" / "validate.py").exists(),
    "validate.py not present yet",
)
class HookRuntimeEditTests(unittest.TestCase):
    def test_cursor_edit_event_reports_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            dart_file = Path(temp) / "bad.dart"
            dart_file.write_text("var x = 1;\n", encoding="utf-8")

            payload = json.dumps({"tool_input": {"path": str(dart_file)}})
            buffer = io.StringIO()
            with mock.patch("sys.stdin", io.StringIO(payload)), mock.patch(
                "sys.stdout", buffer
            ):
                exit_code = main(["--client", "cursor", "--event", "edit"])

            self.assertEqual(exit_code, 0)
            output = json.loads(buffer.getvalue())
            self.assertIn("additional_context", output)
            self.assertIn("FP GUARD", output["additional_context"])
            self.assertIn("var", output["additional_context"])


class RuleContextTests(unittest.TestCase):
    """Rules must reach the agent's context, not only the vendored tree."""

    def test_claude_rules_are_path_scoped_like_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            install(dest, ("claude",))
            rules = dest / ".claude" / "rules"
            core = (rules / "fp-core.md").read_text(encoding="utf-8")
            typescript = (rules / "fp-typescript.md").read_text(encoding="utf-8")
            self.assertFalse(core.startswith("---"), "core rule must load always")
            self.assertIn("## Algebra", core)
            self.assertTrue(typescript.startswith('---\npaths:\n  - "**/*.ts"\n---'))
            self.assertIn("## Effects as Capabilities", typescript)

            uninstall(dest)
            self.assertFalse(rules.exists())

    def test_codex_agents_block_is_managed_and_reversible(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            agents = dest / "AGENTS.md"
            agents.write_text("# My project\n\nKeep this.\n", encoding="utf-8")

            install(dest, ("codex",))
            install(dest, ("codex",))
            text = agents.read_text(encoding="utf-8")
            self.assertEqual(text.count("<!-- fp-enforcer:begin"), 1)
            self.assertIn("Keep this.", text)
            self.assertIn("## Algebra", text)
            self.assertIn("Applies to: `**/*.ts`", text)

            uninstall(dest)
            self.assertEqual(agents.read_text(encoding="utf-8"), "# My project\n\nKeep this.\n")

    def test_codex_agents_file_created_by_install_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            install(dest, ("codex",))
            self.assertTrue((dest / "AGENTS.md").is_file())
            uninstall(dest)
            self.assertFalse((dest / "AGENTS.md").exists())


class HookRuntimeStopTests(unittest.TestCase):
    def test_stop_runs_dart_analyze_on_changed_dart_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            dart_file = Path(temp) / "a.dart"
            dart_file.write_text("void main() {}\n", encoding="utf-8")
            failing = mock.Mock(returncode=1, stdout="info - bad\n", stderr="")
            buffer = io.StringIO()
            with mock.patch(
                "fp_enforcer.hook_runtime._repo_root", return_value=Path(temp)
            ), mock.patch(
                "fp_enforcer.hook_runtime._changed_paths", return_value=(dart_file,)
            ), mock.patch(
                "fp_enforcer.hook_runtime.shutil.which", return_value="/bin/dart"
            ), mock.patch(
                "fp_enforcer.hook_runtime.subprocess.run", return_value=failing
            ) as run, mock.patch("sys.stdin", io.StringIO("{}")), mock.patch(
                "sys.stdout", buffer
            ):
                exit_code = main(["--client", "claude", "--event", "stop"])

            self.assertEqual(exit_code, 0)
            self.assertIn("timeout", run.call_args.kwargs)
            output = json.loads(buffer.getvalue())
            self.assertEqual(output["decision"], "block")
            self.assertIn("dart analyze", output["reason"])


class SourceRootTests(unittest.TestCase):
    def test_source_root_points_at_package(self) -> None:
        self.assertEqual(SOURCE_ROOT, _PROJECT_ROOT / "fp_enforcer")


if __name__ == "__main__":
    unittest.main()
