"""Tests for fp_enforcer.hook_runtime: findings are scoped to changed lines."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

from fp_enforcer import hook_runtime
from fp_enforcer.hook_runtime import _DIFF_BASE_ENV, _diff_base, main


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        (
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            "-c",
            "commit.gpgsign=false",
            *args,
        ),
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _write(repo: Path, name: str, text: str) -> None:
    target = repo / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _commit(repo: Path, files: dict[str, str], message: str) -> None:
    for name, text in files.items():
        _write(repo, name, text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


@contextlib.contextmanager
def _workspace(git: bool = True) -> Iterator[Path]:
    previous = os.getcwd()
    with tempfile.TemporaryDirectory() as temp, mock.patch.dict(os.environ):
        os.environ.pop(_DIFF_BASE_ENV, None)
        repo = Path(temp).resolve()
        if git:
            _git(repo, "init", "-q")
        try:
            os.chdir(repo)
            yield repo
        finally:
            os.chdir(previous)


def _run_hook(event: str, payload: dict | None = None) -> dict:
    buffer = io.StringIO()
    stdin = io.StringIO(json.dumps(payload or {}))
    with mock.patch("sys.stdin", stdin), mock.patch("sys.stdout", buffer):
        exit_code = main(["--client", "claude", "--event", event])
    if exit_code != 0:
        raise AssertionError(f"hook exited with {exit_code}")
    return json.loads(buffer.getvalue())


def _edit(path: str | Path) -> dict:
    return _run_hook("edit", {"tool_input": {"file_path": str(path)}})


def _stop() -> dict:
    return _run_hook("stop")


def _reason(output: dict) -> str:
    return output.get("reason", "")


class DiffBaseTests(unittest.TestCase):
    def test_unset_defaults_to_head(self) -> None:
        with mock.patch.dict(os.environ):
            os.environ.pop(_DIFF_BASE_ENV, None)
            self.assertEqual(_diff_base(), "HEAD")

    def test_empty_defaults_to_head(self) -> None:
        with mock.patch.dict(os.environ, {_DIFF_BASE_ENV: "   "}):
            self.assertEqual(_diff_base(), "HEAD")

    def test_set_value_is_stripped_and_used(self) -> None:
        with mock.patch.dict(os.environ, {_DIFF_BASE_ENV: " HEAD~2 "}):
            self.assertEqual(_diff_base(), "HEAD~2")


class EditScopeTests(unittest.TestCase):
    def test_legacy_finding_on_untouched_line_is_not_reported(self) -> None:
        with _workspace() as repo:
            _commit(repo, {"a.ts": "let legacy = 1;\nconst ok = 1;\n"}, "base")
            _write(repo, "a.ts", "let legacy = 1;\nconst fine = 2;\n")
            self.assertEqual(_edit(repo / "a.ts"), {})

    def test_finding_on_changed_line_is_reported_and_legacy_is_not(self) -> None:
        with _workspace() as repo:
            _commit(repo, {"a.ts": "let legacy = 1;\nconst ok = 1;\n"}, "base")
            _write(repo, "a.ts", "let legacy = 1;\nlet added = 2;\n")
            reason = _reason(_edit(repo / "a.ts"))
            self.assertIn(f"{repo / 'a.ts'}:2: [no-let]", reason)
            self.assertNotIn(":1: [no-let]", reason)
            self.assertTrue(reason.startswith("FP GUARD: "))

    def test_added_line_at_end_of_file_is_reported(self) -> None:
        with _workspace() as repo:
            _commit(repo, {"a.ts": "const a = 1;\n"}, "base")
            _write(repo, "a.ts", "const a = 1;\nlet tail = 2;\n")
            self.assertIn(":2: [no-let]", _reason(_edit(repo / "a.ts")))

    def test_untracked_file_reports_every_finding(self) -> None:
        with _workspace() as repo:
            _commit(repo, {"README.md": "x\n"}, "base")
            _write(repo, "c.ts", "let one = 1;\nlet two = 2;\n")
            reason = _reason(_edit(repo / "c.ts"))
            self.assertIn(":1: [no-let]", reason)
            self.assertIn(":2: [no-let]", reason)

    def test_block_comment_context_is_respected(self) -> None:
        with _workspace() as repo:
            _commit(
                repo,
                {"a.ts": "/*\nplain text\n*/\nconst ok = 1;\n"},
                "base",
            )
            _write(repo, "a.ts", "/*\nlet hidden = 1;\n*/\nconst ok = 1;\n")
            self.assertEqual(_edit(repo / "a.ts"), {})

    def test_relative_path_from_repo_root(self) -> None:
        with _workspace() as repo:
            _commit(repo, {"src/a.ts": "let legacy = 1;\n"}, "base")
            _write(repo, "src/a.ts", "let legacy = 1;\nlet added = 2;\n")
            reason = _reason(_edit("src/a.ts"))
            self.assertIn("src/a.ts:2: [no-let]", reason)
            self.assertEqual(reason.count("[no-let]"), 1)

    def test_relative_path_from_subdirectory(self) -> None:
        with _workspace() as repo:
            _commit(repo, {"src/a.ts": "let legacy = 1;\n"}, "base")
            _write(repo, "src/a.ts", "let legacy = 1;\nlet added = 2;\n")
            os.chdir(repo / "src")
            reason = _reason(_edit("a.ts"))
            self.assertIn("a.ts:2: [no-let]", reason)
            self.assertEqual(reason.count("[no-let]"), 1)

    def test_absolute_path_matches_relative_result(self) -> None:
        with _workspace() as repo:
            _commit(repo, {"src/a.ts": "let legacy = 1;\n"}, "base")
            _write(repo, "src/a.ts", "let legacy = 1;\nlet added = 2;\n")
            reason = _reason(_edit(repo / "src" / "a.ts"))
            self.assertIn(f"{repo / 'src' / 'a.ts'}:2: [no-let]", reason)
            self.assertEqual(reason.count("[no-let]"), 1)


class StopScopeTests(unittest.TestCase):
    def test_legacy_finding_on_untouched_line_is_not_reported(self) -> None:
        with _workspace() as repo:
            _commit(repo, {"a.ts": "let legacy = 1;\nconst ok = 1;\n"}, "base")
            _write(repo, "a.ts", "let legacy = 1;\nconst fine = 2;\n")
            self.assertEqual(_stop(), {})

    def test_changed_line_is_reported_on_stop(self) -> None:
        with _workspace() as repo:
            _commit(repo, {"a.ts": "let legacy = 1;\nconst ok = 1;\n"}, "base")
            _write(repo, "a.ts", "let legacy = 1;\nlet added = 2;\n")
            reason = _reason(_stop())
            self.assertIn("a.ts:2: [no-let]", reason)
            self.assertNotIn(":1: [no-let]", reason)

    def test_two_tracked_files_report_only_new_lines(self) -> None:
        with _workspace() as repo:
            _commit(
                repo,
                {"a.ts": "let legacy = 1;\n", "b.ts": "let legacy = 1;\n"},
                "base",
            )
            _write(repo, "a.ts", "let legacy = 1;\nlet new = 2;\n")
            _write(repo, "b.ts", "let legacy = 1;\nlet new = 2;\n")
            reason = _reason(_stop())
            self.assertIn("a.ts:2: [no-let]", reason)
            self.assertIn("b.ts:2: [no-let]", reason)
            self.assertEqual(reason.count("[no-let]"), 2)

    def test_untracked_file_reports_every_finding(self) -> None:
        with _workspace() as repo:
            _commit(repo, {"README.md": "x\n"}, "base")
            _write(repo, "c.ts", "let one = 1;\nlet two = 2;\n")
            reason = _reason(_stop())
            self.assertIn("c.ts:1: [no-let]", reason)
            self.assertIn("c.ts:2: [no-let]", reason)

    def test_block_comment_context_is_respected(self) -> None:
        with _workspace() as repo:
            _commit(
                repo,
                {"a.ts": "/*\nplain text\n*/\nconst ok = 1;\n"},
                "base",
            )
            _write(repo, "a.ts", "/*\nlet hidden = 1;\n*/\nconst ok = 1;\n")
            self.assertEqual(_stop(), {})

    def test_subdirectory_run_finds_all_changed_files(self) -> None:
        with _workspace() as repo:
            _commit(
                repo,
                {"src/a.ts": "let legacy = 1;\n", "root.ts": "let legacy = 1;\n"},
                "base",
            )
            _write(repo, "src/a.ts", "let legacy = 1;\nlet added = 2;\n")
            _write(repo, "root.ts", "let legacy = 1;\nlet rootnew = 3;\n")
            _write(repo, "src/new.ts", "let fresh = 1;\n")
            os.chdir(repo / "src")
            reason = _reason(_stop())
            self.assertIn("src/a.ts:2: [no-let]", reason)
            self.assertIn("src/new.ts:1: [no-let]", reason)
            self.assertIn("root.ts:2: [no-let]", reason)
            self.assertNotIn("src/a.ts:1: [no-let]", reason)
            self.assertNotIn("root.ts:1: [no-let]", reason)


class DiffBaseBehaviourTests(unittest.TestCase):
    def _two_commits(self, repo: Path) -> None:
        _commit(repo, {"a.ts": "let legacy = 1;\n"}, "first")
        _commit(repo, {"a.ts": "let legacy = 1;\nlet added = 2;\n"}, "second")

    def test_default_base_is_head_so_committed_work_is_clean(self) -> None:
        with _workspace() as repo:
            self._two_commits(repo)
            self.assertEqual(_edit(repo / "a.ts"), {})
            self.assertEqual(_stop(), {})

    def test_env_base_reports_line_from_second_commit_for_edit_and_stop(self) -> None:
        with _workspace() as repo:
            self._two_commits(repo)
            with mock.patch.dict(os.environ, {_DIFF_BASE_ENV: "HEAD~1"}):
                edit_reason = _reason(_edit(repo / "a.ts"))
                stop_reason = _reason(_stop())
            for reason in (edit_reason, stop_reason):
                self.assertIn("a.ts:2: [no-let]", reason)
                self.assertNotIn("a.ts:1: [no-let]", reason)


class FallbackTests(unittest.TestCase):
    def test_bad_base_falls_back_to_whole_file_for_edit_and_stop(self) -> None:
        with _workspace() as repo:
            _commit(repo, {"a.ts": "let legacy = 1;\n"}, "base")
            _write(repo, "a.ts", "let legacy = 1;\nlet new = 2;\n")
            with mock.patch.dict(os.environ, {_DIFF_BASE_ENV: "no-such-rev"}):
                edit_reason = _reason(_edit(repo / "a.ts"))
                stop_reason = _reason(_stop())
            for reason in (edit_reason, stop_reason):
                self.assertIn("a.ts:1: [no-let]", reason)
                self.assertIn("a.ts:2: [no-let]", reason)

    def test_plain_directory_edit_scans_whole_file(self) -> None:
        with _workspace(git=False) as plain:
            _write(plain, "a.ts", "let one = 1;\nlet two = 2;\n")
            reason = _reason(_edit(plain / "a.ts"))
            self.assertIn(":1: [no-let]", reason)
            self.assertIn(":2: [no-let]", reason)

    def test_plain_directory_stop_prints_nothing(self) -> None:
        with _workspace(git=False) as plain:
            _write(plain, "a.ts", "let one = 1;\n")
            self.assertEqual(_stop(), {})

    def test_git_unavailable_edit_scans_whole_file_and_stop_is_empty(self) -> None:
        with _workspace() as repo:
            _commit(repo, {"a.ts": "let legacy = 1;\n"}, "base")
            _write(repo, "a.ts", "let legacy = 1;\nlet new = 2;\n")
            with mock.patch.object(hook_runtime, "_run_git", return_value=None):
                edit_reason = _reason(_edit(repo / "a.ts"))
                stop_output = _stop()
            self.assertIn("a.ts:1: [no-let]", edit_reason)
            self.assertIn("a.ts:2: [no-let]", edit_reason)
            self.assertEqual(stop_output, {})


if __name__ == "__main__":
    unittest.main()
