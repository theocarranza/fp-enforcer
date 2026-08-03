# FP Assimilate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the loop from library detection to enforcement — activate curated per-library and per-language-feature pattern packs in a target project, gated by embedded self-tests.

**Architecture:** The canonical repo ships inert curated packs under `rules/patterns/libraries/<id>.json`, each carrying a `self_test` payload (code strings that must produce violations, and code strings that must produce zero). A new `fp_enforcer/assimilate.py` detects FP libraries (reusing `learn.detect_libraries`) and language features (new SDK-constraint detection), selects matching curated packs, copies them into the project's `.fp-enforcer/rules/patterns/learned/` — but only after each pack passes its self-test (fail-closed). The scanner learns to match *multiple* packs per file (`packs_for`) and to load the `learned/` subdirectory, so hooks pick up activated packs automatically.

**Tech Stack:** Python 3.10+ stdlib only; unittest; existing `fp_enforcer` modules.

## Global Constraints

- Python 3.10+ standard library only — no third-party dependencies.
- Code style: frozen dataclasses, pure functions, `match` statements, effects at the edges (the functional style the product enforces).
- TDD: failing test first, minimal implementation, then commit.
- Learned/activated packs are NEVER written into the canonical `rules/patterns/` root — only into `<dest>/.fp-enforcer/rules/patterns/learned/`.
- Pack JSON files may carry extra keys (`library`, `feature`, `self_test`); the existing `_pack_from_dict` ignores unknown keys and must stay that way.
- Commit style: imperative subject, no conventional-commit prefixes (match `git log`).
- After code changes, refresh the repo's self-hosted harness with `python3 -m fp_enforcer install --client cursor --dest .` (idempotent; do NOT use `--client all` — it would create `.claude/`, `.codex/`, `.agent/` scaffolding the repo does not have).

---

### Task 1: Multi-pack scanning in `validate.py`

Today `pack_for` returns the FIRST pack matching a file suffix, so a second pack for the same language is silently dead. Add `packs_for` (all matching packs), dedupe violations, and teach `load_packs` to include a `learned/` subdirectory.

**Files:**
- Modify: `fp_enforcer/validate.py` (add `packs_for`, `load_pack`, `_dedupe`; rework `pack_for`, `scan_file`, `_process_diff_line`, `scan_diff`, `load_packs`)
- Test: `tests/test_validate.py`

**Interfaces:**
- Produces: `validate.packs_for(packs: tuple[PatternPack, ...], path: str) -> tuple[PatternPack, ...]` — all packs whose suffixes match `path` and whose `exclude_suffixes` do not.
- Produces: `validate.load_pack(path: Path) -> PatternPack` — load one pack JSON file (public wrapper over `_pack_from_dict`).
- Keeps: `validate.pack_for(...) -> PatternPack | None` — same signature, reimplemented via `packs_for` (first match or None). `hook_runtime.py` keeps using it for "is this file scannable" checks.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_validate.py`:

```python
def _dart_extension_pack() -> PatternPack:
    return PatternPack(
        language="dart",
        suffixes=(".dart",),
        exclude_suffixes=(),
        patterns=(
            Pattern(
                id="no-dynamic",
                regex=r"\bdynamic\b",
                message="no dynamic",
                rule="fp-dart-style 1",
            ),
        ),
    )


class PacksForTests(unittest.TestCase):
    def test_packs_for_returns_all_matching(self) -> None:
        packs = (_dart_pack(), _dart_extension_pack())
        self.assertEqual(len(validate.packs_for(packs, "lib/a.dart")), 2)

    def test_packs_for_respects_each_pack_exclusions(self) -> None:
        packs = (_dart_pack(), _dart_extension_pack())
        self.assertEqual(len(validate.packs_for(packs, "lib/a.g.dart")), 1)

    def test_packs_for_no_match_returns_empty(self) -> None:
        packs = (_dart_pack(), _dart_extension_pack())
        self.assertEqual(validate.packs_for(packs, "lib/a.md"), ())

    def test_pack_for_still_returns_first_match(self) -> None:
        packs = (_dart_pack(), _dart_extension_pack())
        matched = validate.pack_for(packs, "lib/a.dart")
        self.assertIsNotNone(matched)
        self.assertEqual(matched.language, "dart")


class MultiPackScanTests(unittest.TestCase):
    def test_scan_file_reports_from_all_matching_packs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sample.dart"
            target.write_text("dynamic x = 1;\n", encoding="utf-8")
            packs = (_dart_pack(), _dart_extension_pack())
            violations = validate.scan_file(packs, target)
            self.assertEqual(
                {item.pattern_id for item in violations}, {"no-dynamic"}
            )

    def test_identical_violations_across_packs_deduped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sample.dart"
            target.write_text("dynamic x = 1;\n", encoding="utf-8")
            packs = (_dart_extension_pack(), _dart_extension_pack())
            violations = validate.scan_file(packs, target)
            self.assertEqual(len(violations), 1)

    def test_scan_diff_reports_from_all_matching_packs(self) -> None:
        packs = (_dart_pack(), _dart_extension_pack())
        diff = "\n".join(
            [
                "--- a/lib/sample.dart",
                "+++ b/lib/sample.dart",
                "@@ -0,0 +1,1 @@",
                "+dynamic count = 0; // fp-allow: nothing",
            ]
        )
        violations = validate.scan_diff(packs, diff)
        self.assertEqual(
            {item.pattern_id for item in violations}, {"no-dynamic"}
        )

    def test_load_packs_includes_learned_subdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            patterns_dir = Path(tmp)
            learned_dir = patterns_dir / "learned"
            learned_dir.mkdir()
            payload = {
                "language": "dart",
                "suffixes": [".dart"],
                "exclude_suffixes": [],
                "patterns": [
                    {"id": "p", "regex": "x", "message": "m", "rule": "r"}
                ],
            }
            (patterns_dir / "dart.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            (learned_dir / "extra.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            packs = validate.load_packs(patterns_dir)
            self.assertEqual(len(packs), 2)

    def test_load_pack_reads_single_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dart.json"
            payload = {
                "language": "dart",
                "suffixes": [".dart"],
                "exclude_suffixes": [],
                "patterns": [
                    {"id": "p", "regex": "x", "message": "m", "rule": "r"}
                ],
                "self_test": {"violations": [], "clean": []},
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            pack = validate.load_pack(path)
            self.assertEqual(pack.language, "dart")
            self.assertEqual(pack.patterns[0].id, "p")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_validate -v 2>&1 | tail -15`
Expected: FAIL — `AttributeError: module 'fp_enforcer.validate' has no attribute 'packs_for'`

- [ ] **Step 3: Implement multi-pack scanning**

In `fp_enforcer/validate.py`, replace `pack_for` and add the new helpers:

```python
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
```

Replace `load_packs` and add `load_pack`:

```python
def load_pack(path: Path) -> PatternPack:
    return _pack_from_dict(path.stem, json.loads(path.read_text(encoding="utf-8")))


def load_packs(patterns_dir: Path) -> tuple[PatternPack, ...]:
    json_paths = sorted(patterns_dir.glob("*.json")) + sorted(
        (patterns_dir / "learned").glob("*.json")
    )
    return tuple(load_pack(path) for path in json_paths)
```

Add `_dedupe` and rework `scan_file`:

```python
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
```

In `_process_diff_line`, replace the `pack_for` branch:

```python
        case str() if line.startswith("+") and not line.startswith("+++"):
            found = tuple(
                violation
                for pack in packs_for(packs, target_path)
                for violation in _scan_added_line(pack, target_path, new_line, line[1:])
            )
            return (target_path, new_line + 1, violations + found)
```

Change `scan_diff`'s final line from `return state[2]` to:

```python
    return _dedupe(state[2])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: `OK` — all existing 44 tests plus the 10 new ones pass (54 total). Existing tests are unaffected because single-pack behavior is unchanged and `dict.fromkeys` preserves order.

- [ ] **Step 5: Commit**

```bash
git add fp_enforcer/validate.py tests/test_validate.py
git commit -m "Support multiple pattern packs per language in the scanner

pack_for returned only the first suffix-matching pack, so a second pack
for the same language was silently dead. packs_for returns all matching
packs, violations are deduped, and load_packs picks up a learned/
subdirectory for assimilated packs."
```

---

### Task 2: Curated packs with embedded self-tests

Author the first two curated packs — `rxjs` (TypeScript library axis) and `dart3` (language-feature axis) — under `rules/patterns/libraries/`. Each carries a `self_test` payload: code strings that must produce at least one violation, and code strings that must produce zero. The glob in `load_packs` is non-recursive, so these stay inert until assimilate copies them into a project's `learned/` dir.

**Files:**
- Create: `rules/patterns/libraries/rxjs.json`
- Create: `rules/patterns/libraries/dart3.json`
- Test: `tests/test_assimilate.py` (new file; the test lives here because Task 3 adds the rest of the assimilate test suite)

**Interfaces:**
- Consumes: `validate.load_pack(path)`, `validate.scan_text(pack, text, path)` from Task 1.
- Produces: pack JSON convention — every curated pack lives at `rules/patterns/libraries/<id>.json` where `<id>` equals the library id from `learn.detect_libraries` (e.g. `rxjs`) or the feature id from `assimilate.detect_language_features` (e.g. `dart3`). The `self_test` field shape is `{"violations": [str, ...], "clean": [str, ...]}`.
- Produces: `assimilate.curated_pack_paths(source_root: Path) -> tuple[Path, ...]` and `assimilate.pack_self_test_failures(path: Path) -> tuple[str, ...]` (implemented in Task 3, used by this task's test — write the test against them now; it fails until Task 3 lands, so implement this task and Task 3 before running).

Note on ordering: this task's verification depends on Task 3's `assimilate` module. Implement the pack files and the test here, then verify at the end of Task 3, and commit both tasks' work in Task 3's commit step. If strict one-commit-per-task is preferred, commit the pack JSON files alone after writing them and let Task 3 carry the test.

- [ ] **Step 1: Write the curated pack files**

Create `rules/patterns/libraries/rxjs.json`:

```json
{
  "library": "rxjs",
  "language": "typescript",
  "suffixes": [".ts", ".tsx"],
  "exclude_suffixes": [".d.ts"],
  "patterns": [
    {"id": "no-manual-subscribe", "regex": "\\.subscribe\\s*\\(", "message": "compose declaratively; subscribe only at the edge with takeUntil or managed Subscription disposal", "rule": "fp-rxdart 1 / rxjs profile"},
    {"id": "no-unbounded-replay-ts", "regex": "new\\s+ReplaySubject\\s*<[^>]*>\\s*\\(\\s*\\)", "message": "ReplaySubject requires an explicit bufferSize bound", "rule": "fp-rxdart memory 2 / rxjs profile"}
  ],
  "self_test": {
    "violations": [
      "source$.pipe(map(load)).subscribe((value) => render(value));",
      "const bus = new ReplaySubject<string>();"
    ],
    "clean": [
      "const sub = source$.pipe(takeUntil(destroy$)).subscribe(render); // fp-allow: no-manual-subscribe — edge disposal, rxjs profile",
      "const bus = new ReplaySubject<string>(5);"
    ]
  }
}
```

Create `rules/patterns/libraries/dart3.json`:

```json
{
  "feature": "dart3",
  "language": "dart",
  "suffixes": [".dart"],
  "exclude_suffixes": [".g.dart", ".freezed.dart", ".gr.dart", ".mocks.dart"],
  "patterns": [
    {"id": "prefer-switch-expression", "regex": "^\\s*switch\\s*\\(", "message": "prefer switch expressions over switch statements", "rule": "fp-dart-style design 4 / dart 3"}
  ],
  "self_test": {
    "violations": [
      "  switch (state) {",
      "switch (value) {"
    ],
    "clean": [
      "final label = switch (state) {",
      "      _ => 'idle',",
      "String describe(State s) => switch (s) {"
    ]
  }
}
```

- [ ] **Step 2: Write the failing self-test runner test**

Create `tests/test_assimilate.py`:

```python
"""Tests for fp_enforcer.assimilate."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fp_enforcer import assimilate


class CuratedPackTests(unittest.TestCase):
    def test_every_curated_pack_passes_its_self_test(self) -> None:
        failures = tuple(
            failure
            for path in assimilate.curated_pack_paths(assimilate.SOURCE_ROOT)
            for failure in assimilate.pack_self_test_failures(path)
        )
        self.assertEqual(failures, ())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m unittest tests.test_assimilate -v 2>&1 | tail -3`
Expected: FAIL — `ModuleNotFoundError: No module named 'fp_enforcer.assimilate'` (Task 3 creates it).

- [ ] **Step 4: Commit the pack files (optional now, or fold into Task 3's commit)**

```bash
git add rules/patterns/libraries/rxjs.json rules/patterns/libraries/dart3.json
git commit -m "Add curated rxjs and dart3 pattern packs with self-tests"
```

---

### Task 3: `fp_enforcer/assimilate.py` core

Detection (libraries via `learn`, language features via SDK constraint), pack selection, fail-closed self-test gate, and activation into the project's `learned/` dir.

**Files:**
- Create: `fp_enforcer/assimilate.py`
- Test: `tests/test_assimilate.py`

**Interfaces:**
- Consumes: `learn.detect_libraries(root) -> tuple[str, ...]`; `validate.load_pack(path)`, `validate.scan_text(...)` from Task 1; curated packs from Task 2.
- Produces: `assimilate.SOURCE_ROOT: Path`
- Produces: `assimilate.ActivatedPack` — frozen dataclass, fields `pack_id: str`, `path: Path`.
- Produces: `assimilate.AssimilateReport` — frozen dataclass, fields `activated: tuple[ActivatedPack, ...]`, `gate_failures: tuple[str, ...]`.
- Produces: `assimilate.detect_language_features(root: Path) -> tuple[str, ...]` — `("dart3",)` when the pubspec SDK constraint has major >= 3, else `()`.
- Produces: `assimilate.curated_pack_paths(source_root: Path) -> tuple[Path, ...]`
- Produces: `assimilate.select_packs(source_root: Path, ids: tuple[str, ...]) -> tuple[Path, ...]`
- Produces: `assimilate.pack_self_test_failures(path: Path) -> tuple[str, ...]` — `()` when the pack passes (or has no self_test).
- Produces: `assimilate.run(dest: Path, source_root: Path = SOURCE_ROOT) -> AssimilateReport` — used by the CLI in Task 4.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_assimilate.py`:

```python
class DetectLanguageFeaturesTests(unittest.TestCase):
    def test_dart3_detected_from_sdk_constraint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pubspec.yaml").write_text(
                "name: app\nenvironment:\n  sdk: ^3.4.0\n", encoding="utf-8"
            )
            self.assertEqual(assimilate.detect_language_features(root), ("dart3",))

    def test_dart2_yields_no_features(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pubspec.yaml").write_text(
                "name: app\nenvironment:\n  sdk: ^2.19.0\n", encoding="utf-8"
            )
            self.assertEqual(assimilate.detect_language_features(root), ())

    def test_missing_pubspec_yields_no_features(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(assimilate.detect_language_features(Path(tmp)), ())


class SelectPacksTests(unittest.TestCase):
    def test_selects_only_detected_ids(self) -> None:
        selected = assimilate.select_packs(assimilate.SOURCE_ROOT, ("rxjs",))
        self.assertEqual([path.stem for path in selected], ["rxjs"])

    def test_unknown_ids_select_nothing(self) -> None:
        self.assertEqual(
            assimilate.select_packs(assimilate.SOURCE_ROOT, ("cobol",)), ()
        )


class RunTests(unittest.TestCase):
    def test_run_activates_packs_for_detected_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pubspec.yaml").write_text(
                "name: app\nenvironment:\n  sdk: ^3.4.0\n"
                "dependencies:\n  rxdart: ^0.28.0\n",
                encoding="utf-8",
            )
            (root / "package.json").write_text(
                json.dumps({"dependencies": {"rxjs": "^7.0.0"}}),
                encoding="utf-8",
            )
            report = assimilate.run(root)
            self.assertEqual(report.gate_failures, ())
            self.assertEqual(
                sorted(item.pack_id for item in report.activated),
                ["dart3", "rxjs"],
            )
            for item in report.activated:
                self.assertTrue(item.path.is_file())
                self.assertIn("learned", item.path.parts)

    def test_run_with_no_libraries_activates_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = assimilate.run(Path(tmp))
            self.assertEqual(report.activated, ())
            self.assertEqual(report.gate_failures, ())

    def test_gate_failure_blocks_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "src"
            library_dir = source / "rules" / "patterns" / "libraries"
            library_dir.mkdir(parents=True)
            payload = {
                "feature": "dart3",
                "language": "dart",
                "suffixes": [".dart"],
                "exclude_suffixes": [],
                "patterns": [
                    {
                        "id": "no-foo",
                        "regex": "\\bfoo\\b",
                        "message": "m",
                        "rule": "r",
                    }
                ],
                "self_test": {"violations": ["bar();"], "clean": []},
            }
            (library_dir / "dart3.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            dest = Path(tmp) / "dest"
            dest.mkdir()
            (dest / "pubspec.yaml").write_text(
                "name: app\nenvironment:\n  sdk: ^3.4.0\n", encoding="utf-8"
            )
            report = assimilate.run(dest, source_root=source)
            self.assertEqual(report.activated, ())
            self.assertEqual(len(report.gate_failures), 1)
            self.assertIn("dart3", report.gate_failures[0])
```

Note: `test_run_activates_packs_for_detected_project` has `rxdart` in the pubspec but only expects `dart3` and `rxjs` activated — no curated `rxdart.json` exists yet, proving unknown/unpacked libraries are skipped gracefully.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_assimilate -v 2>&1 | tail -3`
Expected: FAIL — `ModuleNotFoundError: No module named 'fp_enforcer.assimilate'`

- [ ] **Step 3: Implement `fp_enforcer/assimilate.py`**

```python
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


def pack_self_test_failures(path: Path) -> tuple[str, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return _self_test_failures(validate.load_pack(path), raw)


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: `OK` — 61 tests (54 from Task 1 plus 7 new assimilate tests, including Task 2's curated self-test).

- [ ] **Step 5: Commit**

```bash
git add fp_enforcer/assimilate.py tests/test_assimilate.py rules/patterns/libraries/
git commit -m "Add assimilate core: detect, select, gate, and activate packs

Curated packs under rules/patterns/libraries/ stay inert until
assimilate copies them into a project's .fp-enforcer/rules/patterns/
learned/ directory. Activation is fail-closed: a pack that misses a
self-test violation string or flags a clean string is not installed.
Language features (dart3) are detected from the pubspec SDK constraint."
```

---

### Task 4: `assimilate` CLI subcommand

**Files:**
- Modify: `fp_enforcer/__main__.py` (import, `_cmd_assimilate`, parser wiring)
- Test: covered transitively by `RunTests` in Task 3 (`assimilate.run` is the whole handler body); no new test file. The verification step is a manual CLI smoke run.

**Interfaces:**
- Consumes: `assimilate.run(dest, source_root) -> AssimilateReport` with fields `activated` (items expose `.pack_id`, `.path`) and `gate_failures` (tuple of str), from Task 3.

- [ ] **Step 1: Implement the subcommand**

In `fp_enforcer/__main__.py`, change the import line:

```python
from fp_enforcer import assimilate, learn, validate
```

Add the handler next to `_cmd_learn`:

```python
def _cmd_assimilate(args: argparse.Namespace) -> int:
    report = assimilate.run(Path(args.dest))
    for item in report.activated:
        print(f"activated: {item.pack_id} -> {item.path}")
    for failure in report.gate_failures:
        print(f"gate failure: {failure}", file=sys.stderr)
    match report.gate_failures:
        case ():
            return 0
        case _:
            return 1
```

Add the parser in `_build_parser`, after the learn parser block:

```python
    assimilate_parser = subparsers.add_parser("assimilate")
    assimilate_parser.add_argument("--dest", required=True)
    assimilate_parser.set_defaults(handler=_cmd_assimilate)
```

- [ ] **Step 2: Smoke-run the CLI**

Run:

```bash
cd /tmp && rm -rf assimilate-smoke && mkdir assimilate-smoke && cd assimilate-smoke
printf 'name: app\nenvironment:\n  sdk: ^3.4.0\n' > pubspec.yaml
printf '{"dependencies": {"rxjs": "^7.0.0"}}' > package.json
cd /mnt/DATA/Projects/Personal/fp-enforcer
python3 -m fp_enforcer assimilate --dest /tmp/assimilate-smoke; echo "exit=$?"
```

Expected output (paths will differ by tmpdir):

```
activated: dart3 -> /tmp/assimilate-smoke/.fp-enforcer/rules/patterns/learned/dart3.json
activated: rxjs -> /tmp/assimilate-smoke/.fp-enforcer/rules/patterns/learned/rxjs.json
exit=0
```

Then confirm the activated packs scan a violating file:

```bash
printf 'const bus = new ReplaySubject<string>();\n' > /tmp/assimilate-smoke/bus.ts
python3 -m fp_enforcer validate --patterns-dir /tmp/assimilate-smoke/.fp-enforcer/rules/patterns /tmp/assimilate-smoke; echo "exit=$?"
```

Expected:

```
/tmp/assimilate-smoke/bus.ts:1: [no-unbounded-replay-ts] ReplaySubject requires an explicit bufferSize bound (fp-rxdart memory 2 / rxjs profile)
exit=1
```

- [ ] **Step 3: Run the full suite**

Run: `python3 -m unittest discover -s tests 2>&1 | tail -3`
Expected: `OK` — 61 tests.

- [ ] **Step 4: Commit**

```bash
git add fp_enforcer/__main__.py
git commit -m "Add assimilate CLI subcommand"
```

---

### Task 5: `fp-assimilate` skill

Agent-facing workflow wrapping the CLI, including the manual authoring path for libraries without a curated pack. Skills are vendored into target projects by `_install_claude` (copies `skills/`); no installer change needed.

**Files:**
- Create: `skills/fp-assimilate/SKILL.md`

**Interfaces:**
- Consumes: `python3 -m fp_enforcer learn --dest` and `python3 -m fp_enforcer assimilate --dest` (Task 4); the curated pack JSON convention from Task 2 (file stem = library/feature id, `self_test` payload).

- [ ] **Step 1: Write the skill**

Create `skills/fp-assimilate/SKILL.md`:

```markdown
---
name: fp-assimilate
description: Use when asked to assimilate FP libraries or language features of a project into enforcement — activates curated pattern packs so validation and hooks understand library-specific anti-patterns.
---

# FP Assimilate

Turn detected FP libraries and language features into active enforcement.
Assimilation has two channels: knowledge profiles (advisory, via `fp-learn`)
and pattern packs (enforced, via this skill).

## Run the pipeline

```bash
python3 -m fp_enforcer learn --dest /path/to/project
python3 -m fp_enforcer assimilate --dest /path/to/project
```

`learn` writes agent-facing profiles to `.fp-enforcer/knowledge/`.
`assimilate` detects FP libraries (`pubspec.yaml`, `package.json`) and
language features (SDK constraints), then activates curated packs from the
canonical `rules/patterns/libraries/` into:

```
<project>/.fp-enforcer/rules/patterns/learned/
```

Activation is fail-closed: every curated pack carries a `self_test` payload
and is only installed when its violation strings produce violations and its
clean strings produce none. Gate failures are printed to stderr and exit 1.

## Verify activation

```bash
python3 -m fp_enforcer validate --patterns-dir <project>/.fp-enforcer/rules/patterns <project>/lib
```

Confirm activated packs fire on real code without flooding false positives.
If a pack is too noisy, remove it from `learned/` or suppress individual
sites with `// fp-allow: <pattern-id>`.

## Libraries without a curated pack

When detection reports a library with no matching pack, author one at
`rules/patterns/libraries/<library>.json` in the fp-enforcer source repo:

1. Copy an existing pack as the template — keep `language`, `suffixes`,
   `exclude_suffixes` consistent with the language.
2. Write only regex-enforceable anti-patterns; idioms and opportunities
   belong in the knowledge profile (see `fp-learn`), not the scanner.
3. Add a `self_test` with at least two `violations` strings (each must be
   flagged) and two `clean` strings (each must not be flagged, suppression
   directives allowed).
4. Run the gate locally:

```bash
python3 -m unittest tests.test_assimilate.CuratedPackTests -v
```

5. Re-run `assimilate` in the target project and verify with `validate`.

Watch suppression density after activation: repeated `fp-allow` directives
for the same pattern id across a project mean the pattern is wrong, not the
code — fix or retract the pack.
```

- [ ] **Step 2: Commit**

```bash
git add skills/fp-assimilate/SKILL.md
git commit -m "Add fp-assimilate skill"
```

---

### Task 6: Docs, badge, and self-hosted refresh

**Files:**
- Modify: `README.md` (capabilities table, CLI examples, tests badge)
- Modify: `CHANGELOG.md` (Unreleased section)
- No code changes; no new tests.

- [ ] **Step 1: Update README**

In the capabilities table, add a row after the Learn row:

```markdown
| Assimilate | `python3 -m fp_enforcer assimilate` activates curated library/language-feature pattern packs detected in the project, gated by embedded self-tests. |
```

In the "Validate and learn" CLI block, add after the learn example:

```bash
# Activate curated pattern packs for detected FP libraries/features
python3 -m fp_enforcer assimilate --dest /path/to/project
```

Count the tests and update the badge on line 6:

Run: `python3 -m unittest discover -s tests 2>&1 | grep "^Ran"`
Expected: `Ran 61 tests` — update the badge to `tests-61%20passing` (adjust to the actual count).

- [ ] **Step 2: Update CHANGELOG**

Under `## [Unreleased]` → `### Added`, add:

```markdown
- Multi-pack scanning: `packs_for` matches every applicable pack per file
  with deduped violations, and `load_packs` picks up a `learned/`
  subdirectory of activated packs.
- `python3 -m fp_enforcer assimilate`: detects FP libraries and language
  features (Dart SDK constraint), activates curated packs from
  `rules/patterns/libraries/` into the project's
  `.fp-enforcer/rules/patterns/learned/`, fail-closed on each pack's
  embedded self-test.
- Curated packs for `rxjs` (no-manual-subscribe, no-unbounded-replay-ts)
  and `dart3` (prefer-switch-expression).
- `fp-assimilate` skill with the activation workflow and the manual
  pack-authoring path for uncurated libraries.
```

- [ ] **Step 3: Refresh the self-hosted harness**

Run: `python3 -m fp_enforcer install --client cursor --dest .`
Expected: prints the vendored/merged file list; `.fp-enforcer/fp_enforcer/assimilate.py` and `.fp-enforcer/rules/patterns/libraries/` now exist. Idempotent — no hook duplication in `.cursor/hooks.json`.

- [ ] **Step 4: Final verification**

Run:

```bash
python3 -m unittest discover -s tests 2>&1 | tail -3
python3 -m fp_enforcer validate tests/harness/violations | wc -l
python3 -m fp_enforcer validate tests/harness/clean tests/harness/suppressions tests/harness/stubs; echo "clean_exit=$?"
```

Expected: `OK` (61 tests); `42`; no output with `clean_exit=0`.

- [ ] **Step 5: Commit**

```bash
git add README.md CHANGELOG.md .fp-enforcer .cursor
git commit -m "Document assimilate and refresh self-hosted harness"
```

---

## Self-Review

**Spec coverage** (from the pitch and critique):
- Run `learn` then extract/activate patterns → Tasks 3-4 (`run` reuses `learn.detect_libraries` before selecting packs); skill Task 5 documents running both.
- Only FP libraries / FP language features → library detection is already FP-scoped in `learn`; the `dart3` feature pack covers language FP features (records/pattern-matching era), Task 3 detection.
- Curated-first, LLM extraction gated → Task 2 curated packs; the skill's "Libraries without a curated pack" section requires a `self_test` and the CuratedPackTests gate for manually authored packs.
- Scanner multi-pack prerequisite → Task 1.
- Learned packs live project-side, never canonical → Global Constraints + `_activate` target path.
- Dedup → `_dedupe` in Task 1.
- Two channels (violations vs opportunities) → skill directs idioms to knowledge profiles, anti-patterns to packs.

**Placeholder scan:** all steps contain complete code and exact commands; no TBDs.

**Type consistency:** `ActivatedPack.pack_id/path`, `AssimilateReport.activated/gate_failures`, `pack_self_test_failures(path) -> tuple[str, ...]`, `curated_pack_paths(source_root) -> tuple[Path, ...]`, `select_packs(source_root, ids)`, `run(dest, source_root=SOURCE_ROOT)` — used identically across Tasks 2-4 and their tests. `validate.packs_for` / `load_pack` signatures match between Task 1 implementation and Task 3 consumption.
