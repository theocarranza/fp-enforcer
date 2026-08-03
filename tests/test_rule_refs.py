"""Ensure every pack `rule` field resolves against rules/*.md numbering."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = ROOT / "rules"
PATTERNS_DIR = RULES_DIR / "patterns"

_HEADING = re.compile(r"^##\s+(.+)$")
_ITEM = re.compile(r"^\s*(\d+)\.\s")
_CLAUSE = re.compile(
    r"(?P<file>fp-[\w-]+)"
    r"(?:\s+(?P<section>[a-z]+))?"
    r"\s+(?P<nums>\d+(?:\s*[-&]\s*\d+)*)"
)


def _section_slug(heading: str) -> str:
    return re.split(r"[\s(&]", heading.strip())[0].lower()


def _index_rule_file(path: Path) -> dict[str, frozenset[int]]:
    text = path.read_text(encoding="utf-8")
    indexed: dict[str, set[int]] = {"": set()}
    section = ""
    for line in text.splitlines():
        match _HEADING.match(line):
            case re.Match() as heading:
                section = _section_slug(heading.group(1))
                indexed.setdefault(section, set())
                continue
            case _:
                pass
        match _ITEM.match(line):
            case re.Match() as item:
                number = int(item.group(1))
                indexed[""].add(number)
                indexed.setdefault(section, set()).add(number)
            case _:
                pass
    return {key: frozenset(values) for key, values in indexed.items()}


def _rule_index() -> dict[str, dict[str, frozenset[int]]]:
    return {
        path.stem: _index_rule_file(path)
        for path in sorted(RULES_DIR.glob("fp-*.md"))
    }


def _expand_nums(spec: str) -> frozenset[int]:
    return frozenset(
        number
        for piece in re.split(r"\s*&\s*", spec)
        for number in _expand_range(piece)
    )


def _expand_range(spec: str) -> frozenset[int]:
    match re.split(r"\s*-\s*", spec.strip()):
        case [single] if single.isdigit():
            return frozenset((int(single),))
        case [start, end] if start.isdigit() and end.isdigit():
            return frozenset(range(int(start), int(end) + 1))
        case _:
            return frozenset()


def _parse_refs(rule: str) -> tuple[tuple[str, str, frozenset[int]], ...]:
    """Parse a pack rule string into (file, section, numbers) triples.

    Supports `fp-core branching 4`, bare `fp-typescript 5`, same-file
    continuations after `/` (`usage 1`, `memory 1`), ranges, and `&`.
    Trailing annotations like `rxjs profile` are ignored.
    """
    body = re.sub(r"(?:/\s*)?(?:\w+\s+profile|dart\d*)\s*$", "", rule).strip()
    refs: list[tuple[str, str, frozenset[int]]] = []
    current_file = ""
    for clause in (part for part in body.split("/") if part.strip()):
        text = clause.strip()
        match _CLAUSE.search(text):
            case re.Match() as found:
                current_file = found.group("file")
                refs.append(
                    (
                        current_file,
                        found.group("section") or "",
                        _expand_nums(found.group("nums")),
                    )
                )
            case _ if current_file:
                match re.fullmatch(
                    r"(?P<section>[a-z]+)\s+(?P<nums>\d+(?:\s*[-&]\s*\d+)*)",
                    text,
                ):
                    case re.Match() as relative:
                        refs.append(
                            (
                                current_file,
                                relative.group("section"),
                                _expand_nums(relative.group("nums")),
                            )
                        )
                    case _:
                        raise AssertionError(
                            f"unparsed rule clause: {text!r} in {rule!r}"
                        )
            case _:
                raise AssertionError(f"unparsed rule clause: {text!r} in {rule!r}")
    return tuple(refs)


def _pack_paths() -> tuple[Path, ...]:
    return tuple(sorted(PATTERNS_DIR.glob("*.json"))) + tuple(
        sorted((PATTERNS_DIR / "libraries").glob("*.json"))
    )


class RuleReferenceTests(unittest.TestCase):
    def test_every_pack_rule_resolves(self) -> None:
        index = _rule_index()
        failures: list[str] = []
        for path in _pack_paths():
            payload = json.loads(path.read_text(encoding="utf-8"))
            for pattern in payload.get("patterns", ()):
                rule = pattern["rule"]
                for file, section, nums in _parse_refs(rule):
                    available = index.get(file, {}).get(section)
                    match available:
                        case None:
                            failures.append(
                                f"{path.name}:{pattern['id']}: unknown "
                                f"{file} {section or '(flat)'} in {rule!r}"
                            )
                        case present if not nums <= present:
                            failures.append(
                                f"{path.name}:{pattern['id']}: "
                                f"{file} {section} {sorted(nums)} not in "
                                f"{sorted(present)} ({rule!r})"
                            )
                        case _:
                            pass
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
