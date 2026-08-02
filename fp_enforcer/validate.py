"""Pure scanning pipeline: load pattern packs and detect violations."""

from __future__ import annotations

import json
import re
from pathlib import Path

from fp_enforcer.core import Pattern, PatternPack, Violation

_SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {".git", "node_modules", "build", ".dart_tool", "__pycache__"}
)


def default_patterns_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "rules" / "patterns"


def _pattern_from_dict(raw: dict[str, object]) -> Pattern:
    return Pattern(
        id=str(raw["id"]),
        regex=str(raw["regex"]),
        message=str(raw["message"]),
        rule=str(raw["rule"]),
    )


def _compile_pattern(pack_name: str, pattern: Pattern) -> re.Pattern[str]:
    try:
        return re.compile(pattern.regex)
    except re.error as exc:
        raise ValueError(
            f"invalid regex in pack {pack_name!r}, pattern {pattern.id!r}: {exc}"
        ) from exc


def _pack_from_dict(name: str, raw: dict[str, object]) -> PatternPack:
    patterns_raw = raw.get("patterns")
    match patterns_raw:
        case list() as items:
            patterns = tuple(_pattern_from_dict(item) for item in items)
        case _:
            patterns = ()

    suffixes_raw = raw.get("suffixes")
    match suffixes_raw:
        case list() as items:
            suffixes = tuple(str(item) for item in items)
        case _:
            suffixes = ()

    exclude_raw = raw.get("exclude_suffixes")
    match exclude_raw:
        case list() as items:
            exclude_suffixes = tuple(str(item) for item in items)
        case _:
            exclude_suffixes = ()

    pack = PatternPack(
        language=str(raw.get("language", name)),
        suffixes=suffixes,
        exclude_suffixes=exclude_suffixes,
        patterns=patterns,
    )
    for pattern in pack.patterns:
        _compile_pattern(name, pattern)
    return pack


def load_packs(patterns_dir: Path) -> tuple[PatternPack, ...]:
    json_paths = sorted(patterns_dir.glob("*.json"))
    return tuple(
        _pack_from_dict(path.stem, json.loads(path.read_text(encoding="utf-8")))
        for path in json_paths
    )


def pack_for(
    packs: tuple[PatternPack, ...], path: str
) -> PatternPack | None:
    for pack in packs:
        if any(path.endswith(suffix) for suffix in pack.exclude_suffixes):
            continue
        if any(path.endswith(suffix) for suffix in pack.suffixes):
            return pack
    return None


def _scan_line(
    path: str,
    line_number: int,
    line_text: str,
    pack: PatternPack,
    compiled: tuple[re.Pattern[str], ...],
) -> tuple[Violation, ...]:
    return tuple(
        Violation(
            path=path,
            line=line_number,
            pattern_id=pattern.id,
            message=pattern.message,
            rule=pattern.rule,
        )
        for pattern, regex in zip(pack.patterns, compiled, strict=True)
        if regex.search(line_text) is not None
    )


def scan_text(pack: PatternPack, text: str, path: str) -> tuple[Violation, ...]:
    compiled = tuple(re.compile(pattern.regex) for pattern in pack.patterns)
    return tuple(
        violation
        for line_number, line_text in enumerate(text.splitlines(), start=1)
        for violation in _scan_line(path, line_number, line_text, pack, compiled)
    )


def scan_file(
    packs: tuple[PatternPack, ...], path: Path
) -> tuple[Violation, ...]:
    pack = pack_for(packs, str(path))
    match pack:
        case None:
            return ()
        case matched:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return ()
            return scan_text(matched, text, str(path))


def _should_skip_dir(name: str) -> bool:
    return name.startswith(".") or name in _SKIP_DIR_NAMES


def _walk_paths(root: Path) -> tuple[Path, ...]:
    def walk(directory: Path) -> tuple[Path, ...]:
        try:
            entries = sorted(directory.iterdir(), key=lambda entry: entry.name)
        except OSError:
            return ()
        return tuple(
            path
            for entry in entries
            for path in (
                (entry,)
                if entry.is_file()
                else walk(entry)
                if entry.is_dir() and not _should_skip_dir(entry.name)
                else ()
            )
        )

    return walk(root)


def scan_paths(
    packs: tuple[PatternPack, ...], paths: tuple[Path, ...]
) -> tuple[Violation, ...]:
    file_paths = tuple(
        path
        for root in paths
        for path in ((root,) if root.is_file() else _walk_paths(root))
    )
    return tuple(
        violation
        for file_path in file_paths
        for violation in scan_file(packs, file_path)
    )


def _parse_hunk_start(header: str) -> int | None:
    match re.search(r"\+(\d+)", header):
        case None:
            return None
        case match_obj:
            return int(match_obj.group(1))


def _scan_added_line(
    pack: PatternPack,
    target_path: str,
    new_line: int,
    content: str,
) -> tuple[Violation, ...]:
    compiled = tuple(re.compile(pattern.regex) for pattern in pack.patterns)
    return _scan_line(target_path, new_line, content, pack, compiled)


def _process_diff_line(
    state: tuple[str, int, tuple[Violation, ...]],
    line: str,
    packs: tuple[PatternPack, ...],
) -> tuple[str, int, tuple[Violation, ...]]:
    target_path, new_line, violations = state
    match line:
        case str() if line.startswith("+++ b/"):
            return (line[6:], new_line, violations)
        case str() if line.startswith("@@"):
            start = _parse_hunk_start(line)
            return (target_path, start if start is not None else 0, violations)
        case str() if line.startswith("+") and not line.startswith("+++"):
            pack = pack_for(packs, target_path)
            match pack:
                case None:
                    return (target_path, new_line + 1, violations)
                case matched:
                    found = _scan_added_line(matched, target_path, new_line, line[1:])
                    return (target_path, new_line + 1, violations + found)
        case str() if line.startswith("-") and not line.startswith("---"):
            return (target_path, new_line, violations)
        case str() if line.startswith(" "):
            return (target_path, new_line + 1, violations)
        case _:
            return (target_path, new_line, violations)


def scan_diff(
    packs: tuple[PatternPack, ...], diff_text: str
) -> tuple[Violation, ...]:
    initial: tuple[str, int, tuple[Violation, ...]] = ("", 0, ())
    state = initial
    for line in diff_text.splitlines():
        state = _process_diff_line(state, line, packs)
    return state[2]


def format_report(violations: tuple[Violation, ...]) -> str:
    return "\n".join(
        f"{item.path}:{item.line}: [{item.pattern_id}] {item.message} ({item.rule})"
        for item in violations
    )
