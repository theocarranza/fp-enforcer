"""Activate curated library and language-feature pattern packs in a project."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from fp_enforcer import learn, validate
from fp_enforcer.core import PatternPack

SOURCE_ROOT = Path(__file__).resolve().parent.parent

_SDK_CONSTRAINT = re.compile(r"^\s+sdk:\s*[\"']?\^?(\d+)\.", re.MULTILINE)


@dataclass(frozen=True)
class ActivatedPack:
    """One curated pack activated in a project."""

    pack_id: str
    path: Path


@dataclass(frozen=True)
class AssimilateReport:
    """Outcome of an assimilate run: activated packs and gate failures."""

    activated: tuple[ActivatedPack, ...]
    gate_failures: tuple[str, ...]


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def detect_language_features(root: Path) -> tuple[str, ...]:
    match _read_text(root / "pubspec.yaml"):
        case str() as text:
            match _SDK_CONSTRAINT.search(text):
                case re.Match() as found if int(found.group(1)) >= 3:
                    return ("dart3",)
                case _:
                    return ()
        case _:
            return ()


def curated_pack_paths(source_root: Path) -> tuple[Path, ...]:
    library_dir = source_root / "rules" / "patterns" / "libraries"
    return tuple(sorted(library_dir.glob("*.json")))


def select_packs(source_root: Path, ids: tuple[str, ...]) -> tuple[Path, ...]:
    wanted = set(ids)
    return tuple(
        path for path in curated_pack_paths(source_root) if path.stem in wanted
    )


def _self_test_failures(pack: PatternPack, raw: dict[str, object]) -> tuple[str, ...]:
    match raw.get("self_test"):
        case dict() as cases:
            pass
        case _:
            return ()
    missed = tuple(
        f"missed violation: {code}"
        for code in cases.get("violations", ())
        if not validate.scan_text(pack, str(code), "self_test")
    )
    noisy = tuple(
        f"clean flagged: {code}"
        for code in cases.get("clean", ())
        if validate.scan_text(pack, str(code), "self_test")
    )
    return missed + noisy


def _load_pack_for_gate(
    path: Path,
) -> tuple[tuple[str, ...], dict[str, object] | None, PatternPack | None]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return ((f"unreadable pack: {exc}",), None, None)
    except json.JSONDecodeError as exc:
        return ((f"malformed pack JSON: {exc}",), None, None)
    try:
        return ((), raw, validate.load_pack(path))
    except (KeyError, TypeError) as exc:
        return ((f"malformed pack: {exc}",), None, None)


def pack_self_test_failures(path: Path) -> tuple[str, ...]:
    load_failures, raw, pack = _load_pack_for_gate(path)
    match (load_failures, raw, pack):
        case (failures, _, _) if failures:
            return failures
        case ((), dict() as parsed, PatternPack() as loaded):
            return _self_test_failures(loaded, parsed)
        case _:
            return ()


def _activate(dest: Path, pack_path: Path) -> tuple[ActivatedPack | None, tuple[str, ...]]:
    match pack_self_test_failures(pack_path):
        case ():
            target = (
                dest
                / ".fp-enforcer"
                / "rules"
                / "patterns"
                / "learned"
                / pack_path.name
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pack_path, target)
            return (ActivatedPack(pack_id=pack_path.stem, path=target), ())
        case failures:
            return (
                None,
                tuple(f"{pack_path.stem}: {item}" for item in failures),
            )


def run(dest: Path, source_root: Path = SOURCE_ROOT) -> AssimilateReport:
    ids = learn.detect_libraries(dest) + detect_language_features(dest)
    results = tuple(_activate(dest, path) for path in select_packs(source_root, ids))
    activated = tuple(item for item, _ in results if item is not None)
    failures = tuple(failure for _, items in results for failure in items)
    return AssimilateReport(activated=activated, gate_failures=failures)
