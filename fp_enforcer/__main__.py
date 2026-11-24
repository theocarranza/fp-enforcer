"""CLI entry point for fp-enforcer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fp_enforcer import assimilate, learn, validate
from fp_enforcer.core import PatternPack, Violation


def _packs_from(patterns_dir: str | None) -> tuple[PatternPack, ...]:
    match patterns_dir:
        case None:
            return validate.load_packs(validate.default_patterns_dir())
        case custom:
            return validate.load_packs(Path(custom))


def _exit_code_for(violations: tuple[Violation, ...]) -> int:
    match violations:
        case ():
            return 0
        case _:
            print(validate.format_report(violations))
            return 1


def _cmd_validate(args: argparse.Namespace) -> int:
    packs = _packs_from(args.patterns_dir)
    match args.diff:
        case None:
            violations = validate.scan_paths(packs, tuple(Path(p) for p in args.paths))
        case diff_arg:
            diff_text = (
                sys.stdin.read()
                if diff_arg == "-"
                else Path(diff_arg).read_text(encoding="utf-8")
            )
            violations = validate.scan_diff(packs, diff_text)
    return _exit_code_for(violations)


def _cmd_scan_legacy(args: argparse.Namespace) -> int:
    packs = _packs_from(args.patterns_dir)
    return _exit_code_for(
        validate.scan_paths(packs, tuple(Path(p) for p in args.paths))
    )


def _cmd_learn(args: argparse.Namespace) -> int:
    written = learn.run(Path(args.dest))
    for path in written:
        print(path)
    return 0


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


def _cmd_install(args: argparse.Namespace) -> int:
    from fp_enforcer.install import install

    clients: tuple[str, ...] = (
        ("cursor", "claude", "codex", "antigravity")
        if args.client == "all"
        else (args.client,)
    )
    written = install(Path(args.dest), clients)
    for path in written:
        print(path)
    return 0


def _cmd_uninstall(args: argparse.Namespace) -> int:
    from fp_enforcer.install import uninstall

    written = uninstall(Path(args.dest))
    for path in written:
        print(path)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fp-enforcer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("paths", nargs="*", default=())
    validate_parser.add_argument("--diff")
    validate_parser.add_argument("--patterns-dir")
    validate_parser.set_defaults(handler=_cmd_validate)

    scan_legacy_parser = subparsers.add_parser(
        "scan-legacy",
        help="scan whole files, including legacy code that the hooks skip",
    )
    scan_legacy_parser.add_argument("paths", nargs="+")
    scan_legacy_parser.add_argument("--patterns-dir")
    scan_legacy_parser.set_defaults(handler=_cmd_scan_legacy)

    learn_parser = subparsers.add_parser("learn")
    learn_parser.add_argument("--dest", required=True)
    learn_parser.set_defaults(handler=_cmd_learn)

    assimilate_parser = subparsers.add_parser("assimilate")
    assimilate_parser.add_argument("--dest", required=True)
    assimilate_parser.set_defaults(handler=_cmd_assimilate)

    wire_parser = subparsers.add_parser(
        "wire",
        aliases=["install"],
        help="wire a project to the installed fp-enforcer (rules, skills, hooks)",
    )
    wire_parser.add_argument(
        "--client",
        required=True,
        choices=("cursor", "claude", "codex", "antigravity", "all"),
    )
    wire_parser.add_argument("--dest", required=True)
    wire_parser.set_defaults(handler=_cmd_install)

    unwire_parser = subparsers.add_parser(
        "unwire",
        aliases=["uninstall"],
        help="remove fp-enforcer wiring from a project",
    )
    unwire_parser.add_argument("--dest", required=True)
    unwire_parser.set_defaults(handler=_cmd_uninstall)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
