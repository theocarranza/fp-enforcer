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


def load_pack(path: Path) -> PatternPack:
    return _pack_from_dict(path.stem, json.loads(path.read_text(encoding="utf-8")))


def load_packs(patterns_dir: Path) -> tuple[PatternPack, ...]:
    json_paths = sorted(patterns_dir.glob("*.json")) + sorted(
        (patterns_dir / "learned").glob("*.json")
    )
    return tuple(load_pack(path) for path in json_paths)


def packs_for(
    packs: tuple[PatternPack, ...], path: str
) -> tuple[PatternPack, ...]:
    return tuple(
        pack
        for pack in packs
        if not any(path.endswith(suffix) for suffix in pack.exclude_suffixes)
        and any(path.endswith(suffix) for suffix in pack.suffixes)
    )


def pack_for(
    packs: tuple[PatternPack, ...], path: str
) -> PatternPack | None:
    match packs_for(packs, path):
        case (first, *_):
            return first
        case ():
            return None


_COMMENT_OR_STRING = re.compile(
    r"'(?:\\.|[^'\\])*'"
    r'|"(?:\\.|[^"\\])*"'
    r"|(?P<line>//)"
    r"|(?P<block>/\*)"
)

_ALLOW_DIRECTIVE = re.compile(r"fp-allow:\s*([a-z0-9-]+(?:\s*,\s*[a-z0-9-]+)*)")


def _first_comment_token(line_text: str) -> re.Match[str] | None:
    return next(
        (
            token
            for token in _COMMENT_OR_STRING.finditer(line_text)
            if token.lastgroup in ("line", "block")
        ),
        None,
    )


def _strip_comments(in_block: bool, line_text: str) -> tuple[str, bool]:
    match in_block:
        case True:
            match line_text.find("*/"):
                case -1:
                    return ("", True)
                case end:
                    return _strip_comments(False, line_text[end + 2 :])
        case False:
            match _first_comment_token(line_text):
                case None:
                    return (line_text, False)
                case token if token.lastgroup == "line":
                    return (line_text[: token.start()], False)
                case token:
                    head = line_text[: token.start()]
                    tail, still_open = _strip_comments(True, line_text[token.end() :])
                    return (head + tail, still_open)


def _allowed_ids(line_text: str) -> frozenset[str]:
    match _ALLOW_DIRECTIVE.search(line_text):
        case None:
            return frozenset()
        case directive:
            return frozenset(re.split(r"\s*,\s*", directive.group(1)))


def _scan_line(
    path: str,
    line_number: int,
    code_text: str,
    allowed: frozenset[str],
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
        if pattern.id not in allowed and regex.search(code_text) is not None
    )


def scan_text(pack: PatternPack, text: str, path: str) -> tuple[Violation, ...]:
    compiled = tuple(re.compile(pattern.regex) for pattern in pack.patterns)
    violations: tuple[Violation, ...] = ()
    in_block = False
    pending: frozenset[str] = frozenset()
    for line_number, line_text in enumerate(text.splitlines(), start=1):
        code_text, in_block = _strip_comments(in_block, line_text)
        allowed = pending | _allowed_ids(line_text)
        violations = violations + _scan_line(
            path, line_number, code_text, allowed, pack, compiled
        )
        pending = allowed if code_text.strip() == "" else frozenset()
    return violations


def _dedupe(violations: tuple[Violation, ...]) -> tuple[Violation, ...]:
    return tuple(dict.fromkeys(violations))


def scan_file(
    packs: tuple[PatternPack, ...], path: Path
) -> tuple[Violation, ...]:
    matched = packs_for(packs, str(path))
    match matched:
        case ():
            return ()
        case _:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return ()
            return _dedupe(
                tuple(
                    violation
                    for pack in matched
                    for violation in scan_text(pack, text, str(path))
                )
            )


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
    code_text, _ = _strip_comments(False, content)
    return _scan_line(
        target_path, new_line, code_text, _allowed_ids(content), pack, compiled
    )


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
            found = tuple(
                violation
                for pack in packs_for(packs, target_path)
                for violation in _scan_added_line(pack, target_path, new_line, line[1:])
            )
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
    return _dedupe(state[2])


def format_report(violations: tuple[Violation, ...]) -> str:
    return "\n".join(
        f"{item.path}:{item.line}: [{item.pattern_id}] {item.message} ({item.rule})"
        for item in violations
    )
