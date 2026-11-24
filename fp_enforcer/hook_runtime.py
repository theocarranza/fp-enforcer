"""Agent hook runtime: edit and completion-gate enforcement."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from fp_enforcer.adapters import by_name
from fp_enforcer.validate import (
    changed_lines,
    default_patterns_dir,
    filter_violations,
    format_report,
    load_packs,
    pack_for,
    scan_file,
)

_DART_ANALYZE_LINE_LIMIT = 30
# Below the 240s Stop-hook timeout wired into host settings.
_DART_ANALYZE_TIMEOUT = 180
_DIFF_BASE_ENV = "FP_ENFORCER_DIFF_BASE"
_RAW_NAMES_GIT_OPTIONS = ("-c", "core.quotepath=false")


def _read_payload() -> dict | None:
    try:
        raw = sys.stdin.read()
        match json.loads(raw):
            case dict() as payload:
                return payload
            case _:
                return None
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None


def _indent_report(report: str) -> str:
    return "\n".join(f"  {line}" for line in report.splitlines())


def _edit_message(path: str, violations: tuple) -> str:
    report = _indent_report(format_report(violations))
    return (
        f"FP GUARD: {path} violates functional programming rules:\n"
        f"{report}\n"
        "Fix these before proceeding; see .fp-enforcer/rules/."
    )


def _diff_base() -> str:
    match os.environ.get(_DIFF_BASE_ENV, "").strip():
        case "":
            return "HEAD"
        case base:
            return base


def _run_git(
    args: tuple[str, ...], cwd: Path | None = None
) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ("git", *args),
            cwd=os.getcwd() if cwd is None else cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None


def _repo_root(cwd: Path | None = None) -> Path | None:
    match _run_git(("rev-parse", "--show-toplevel"), cwd=cwd):
        case subprocess.CompletedProcess() as result if result.returncode == 0:
            root = result.stdout.strip()
            return Path(root) if root else None
        case _:
            return None


def _git_names(result: subprocess.CompletedProcess[str]) -> tuple[str, ...]:
    return tuple(line for line in result.stdout.splitlines() if line)


def _untracked_names(root: Path) -> frozenset[str] | None:
    result = _run_git(
        (*_RAW_NAMES_GIT_OPTIONS, "ls-files", "--others", "--exclude-standard"),
        cwd=root,
    )
    match result:
        case subprocess.CompletedProcess() if result.returncode == 0:
            return frozenset(_git_names(result))
        case _:
            return None


def _changed_line_map(
    root: Path, base: str
) -> Mapping[str, frozenset[int]] | None:
    result = _run_git(
        (
            *_RAW_NAMES_GIT_OPTIONS,
            "diff",
            "-U0",
            "--no-color",
            "--no-ext-diff",
            "--src-prefix=a/",
            "--dst-prefix=b/",
            base,
            "--",
        ),
        cwd=root,
    )
    match result:
        case subprocess.CompletedProcess() if result.returncode == 0:
            return changed_lines(result.stdout)
        case _:
            return None


def _changed_paths(root: Path, base: str = "HEAD") -> tuple[Path, ...]:
    diff = _run_git(
        (*_RAW_NAMES_GIT_OPTIONS, "diff", "--name-only", base, "--"), cwd=root
    )
    untracked = _run_git(
        (*_RAW_NAMES_GIT_OPTIONS, "ls-files", "--others", "--exclude-standard"),
        cwd=root,
    )
    names = frozenset(
        name
        for result in (diff, untracked)
        if result is not None and result.returncode == 0
        for name in _git_names(result)
    )
    return tuple(root / name for name in sorted(names))


def _relative_name(root: Path, path: Path) -> str | None:
    try:
        return (
            (path.parent.resolve() / path.name)
            .relative_to(root.resolve())
            .as_posix()
        )
    except ValueError:
        return None


def _list_base(base: str, changes: Mapping[str, frozenset[int]] | None) -> str:
    match changes:
        case None:
            return "HEAD"
        case _:
            return base


def _is_untracked(path: str, untracked: frozenset[str] | None) -> bool:
    match untracked:
        case None:
            return False
        case names:
            return path in names


def _scope_named(
    violations: tuple,
    path: str,
    changes: Mapping[str, frozenset[int]],
    untracked: frozenset[str] | None,
) -> tuple:
    match (_is_untracked(path, untracked), path in changes, untracked is None):
        case (True, _, _):
            return violations
        case (False, True, _):
            return filter_violations(violations, changes[path])
        case (False, False, True):
            return violations
        case _:
            return ()


def _scope_violations(
    violations: tuple,
    name: str | None,
    changes: Mapping[str, frozenset[int]] | None,
    untracked: frozenset[str] | None,
) -> tuple:
    match (name, changes):
        case (None, _) | (_, None):
            return violations
        case (str() as path, known):
            return _scope_named(violations, path, known, untracked)


def _untracked_unless_listed(
    root: Path, name: str | None, changes: Mapping[str, frozenset[int]] | None
) -> frozenset[str] | None:
    match (name, changes):
        case (str() as path, Mapping() as known) if path in known:
            return None
        case _:
            return _untracked_names(root)


def _edit_violations(path: Path, violations: tuple) -> tuple:
    match _repo_root(path.parent.resolve()):
        case Path() as root:
            name = _relative_name(root, path)
            changes = _changed_line_map(root, _diff_base())
            untracked = _untracked_unless_listed(root, name, changes)
            return _scope_violations(violations, name, changes, untracked)
        case _:
            return violations


def _stop_violations(
    packs: tuple,
    root: Path,
    paths: tuple[Path, ...],
    changes: Mapping[str, frozenset[int]] | None,
    untracked: frozenset[str] | None,
) -> tuple:
    return tuple(
        violation
        for path in paths
        for violation in _scope_violations(
            scan_file(packs, path), _relative_name(root, path), changes, untracked
        )
    )


def _scannable_paths(
    packs: tuple, paths: tuple[Path, ...]
) -> tuple[Path, ...]:
    return tuple(
        path
        for path in paths
        if path.is_file()
        and pack_for(packs, str(path)) is not None
    )


def _dart_analyze_output(dart_files: tuple[Path, ...]) -> str | None:
    if not dart_files or shutil.which("dart") is None:
        return None
    try:
        result = subprocess.run(
            ("dart", "analyze", "--fatal-infos", *(str(path) for path in dart_files)),
            capture_output=True,
            text=True,
            check=False,
            timeout=_DART_ANALYZE_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode == 0:
        return None
    combined = "\n".join(
        line for line in (result.stdout + result.stderr).splitlines() if line.strip()
    )
    lines = combined.splitlines()[:_DART_ANALYZE_LINE_LIMIT]
    return "\n".join(lines) if lines else None


def _stop_message(violations: tuple, analyzer_output: str | None) -> str | None:
    sections: list[str] = []
    if violations:
        sections.append(_indent_report(format_report(violations)))
    if analyzer_output:
        sections.append(
            "dart analyze:\n"
            + "\n".join(f"  {line}" for line in analyzer_output.splitlines())
        )
    match sections:
        case []:
            return None
        case items:
            body = "\n\n".join(items)
            return (
                "FP GUARD (completion gate): resolve these functional-rule "
                f"violations before finishing:\n{body}"
            )


def _handle_edit(adapter, payload: dict) -> None:
    path_str = adapter.extract_path(payload)
    match path_str:
        case str() as candidate if candidate:
            resolved = Path(candidate)
        case _:
            print("{}")
            return

    packs = load_packs(default_patterns_dir())
    if pack_for(packs, path_str) is None or not resolved.is_file():
        print("{}")
        return

    violations = _edit_violations(resolved, scan_file(packs, resolved))
    match violations:
        case ():
            print("{}")
        case found:
            message = _edit_message(path_str, found)
            print(json.dumps(adapter.format_edit(message)))


def _handle_stop(adapter) -> None:
    root = _repo_root()
    match root:
        case Path() as repo_root:
            packs = load_packs(default_patterns_dir())
            base = _diff_base()
            changes = _changed_line_map(repo_root, base)
            changed = _scannable_paths(
                packs, _changed_paths(repo_root, _list_base(base, changes))
            )
            untracked = _untracked_names(repo_root)
            violations = _stop_violations(
                packs, repo_root, changed, changes, untracked
            )
            dart_files = tuple(
                path for path in changed if str(path).endswith(".dart")
            )
            analyzer_output = _dart_analyze_output(dart_files)
            message = _stop_message(violations, analyzer_output)
            match message:
                case str() as text:
                    print(json.dumps(adapter.format_stop(text)))
                case _:
                    print("{}")
        case _:
            print("{}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="fp-enforcer agent hook runtime")
    parser.add_argument(
        "--client",
        required=True,
        choices=("cursor", "claude", "codex", "antigravity"),
    )
    parser.add_argument("--event", required=True, choices=("edit", "stop"))
    args = parser.parse_args(argv)

    match _read_payload():
        case dict() as payload:
            adapter = by_name(args.client)
            match args.event:
                case "edit":
                    _handle_edit(adapter, payload)
                case "stop":
                    _handle_stop(adapter)
        case _:
            print("{}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
