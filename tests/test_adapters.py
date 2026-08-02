"""Tests for vendor hook adapters."""

from __future__ import annotations

import unittest

from fp_enforcer.adapters import by_name
from fp_enforcer.adapters import claude, codex, cursor


class AdapterExtractPathTests(unittest.TestCase):
    def test_cursor_tool_input_path(self) -> None:
        payload = {"tool_input": {"path": "/tmp/example.dart"}}
        self.assertEqual(cursor.extract_path(payload), "/tmp/example.dart")

    def test_cursor_tool_input_file_path(self) -> None:
        payload = {"tool_input": {"file_path": "/tmp/other.dart"}}
        self.assertEqual(cursor.extract_path(payload), "/tmp/other.dart")

    def test_cursor_top_level_file_path(self) -> None:
        payload = {"file_path": "/tmp/top.dart"}
        self.assertEqual(cursor.extract_path(payload), "/tmp/top.dart")

    def test_claude_tool_input_file_path(self) -> None:
        payload = {"tool_input": {"file_path": "/tmp/claude.dart"}}
        self.assertEqual(claude.extract_path(payload), "/tmp/claude.dart")

    def test_codex_arguments_path(self) -> None:
        payload = {"arguments": {"path": "/tmp/codex.ts"}}
        self.assertEqual(codex.extract_path(payload), "/tmp/codex.ts")


class AdapterFormatTests(unittest.TestCase):
    def test_cursor_format_edit(self) -> None:
        result = cursor.format_edit("blocked")
        self.assertEqual(result, {"additional_context": "blocked"})

    def test_cursor_format_stop(self) -> None:
        result = cursor.format_stop("finish later")
        self.assertEqual(result, {"followup_message": "finish later"})

    def test_claude_format_edit(self) -> None:
        result = claude.format_edit("blocked")
        self.assertEqual(result, {"decision": "block", "reason": "blocked"})

    def test_claude_format_stop(self) -> None:
        result = claude.format_stop("blocked")
        self.assertEqual(result, {"decision": "block", "reason": "blocked"})

    def test_codex_format_edit(self) -> None:
        result = codex.format_edit("blocked")
        self.assertEqual(result, {"decision": "block", "reason": "blocked"})

    def test_empty_message_returns_empty_dict(self) -> None:
        self.assertEqual(cursor.format_edit(None), {})
        self.assertEqual(cursor.format_edit(""), {})
        self.assertEqual(claude.format_stop(None), {})


class AdapterRegistryTests(unittest.TestCase):
    def test_by_name_known_clients(self) -> None:
        self.assertIs(by_name("cursor"), cursor)
        self.assertIs(by_name("claude"), claude)
        self.assertIs(by_name("codex"), codex)

    def test_by_name_unknown_raises(self) -> None:
        with self.assertRaises(ValueError):
            by_name("unknown")


if __name__ == "__main__":
    unittest.main()
