"""Agent hook runtime: edit and completion-gate enforcement."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from fp_enforcer.adapters import by_name
from fp_enforcer.validate import (
    default_patterns_dir,
    format_report,
    load_packs,
    pack_for,
    scan_file,
    scan_paths,
)

_DART_ANALYZE_LINE_LIMIT = 30


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


def _run_git(args: tuple[str, ...]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ("git", *args),
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None


def _repo_root() -> Path | None:
    match _run_git(("rev-parse", "--show-toplevel")):
        case subprocess.CompletedProcess() as result if result.returncode == 0:
            root = result.stdout.strip()
            return Path(root) if root else None
        case _:
            return None


def _changed_paths(root: Path) -> tuple[Path, ...]:
    diff = _run_git(("diff", "--name-only", "HEAD"))
    untracked = _run_git(("ls-files", "--others", "--exclude-standard"))
    names = {
        line.strip()
        for result in (diff, untracked)
        if result is not None and result.returncode == 0
        for line in result.stdout.splitlines()
        if line.strip()
    }
    return tuple(root / name for name in sorted(names))


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

    violations = scan_file(packs, resolved)
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
            changed = _scannable_paths(packs, _changed_paths(repo_root))
            violations = scan_paths(packs, changed)
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
