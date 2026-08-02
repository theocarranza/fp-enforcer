"""CLI entry point for fp-enforcer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fp_enforcer import learn, validate


def _cmd_validate(args: argparse.Namespace) -> int:
    patterns_dir = (
        Path(args.patterns_dir)
        if args.patterns_dir is not None
        else validate.default_patterns_dir()
    )
    packs = validate.load_packs(patterns_dir)
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
    match violations:
        case ():
            return 0
        case _:
            print(validate.format_report(violations))
            return 1


def _cmd_learn(args: argparse.Namespace) -> int:
    written = learn.run(Path(args.dest))
    for path in written:
        print(path)
    return 0


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

    learn_parser = subparsers.add_parser("learn")
    learn_parser.add_argument("--dest", required=True)
    learn_parser.set_defaults(handler=_cmd_learn)

    install_parser = subparsers.add_parser("install")
    install_parser.add_argument(
        "--client",
        required=True,
        choices=("cursor", "claude", "codex", "antigravity", "all"),
    )
    install_parser.add_argument("--dest", required=True)
    install_parser.set_defaults(handler=_cmd_install)

    uninstall_parser = subparsers.add_parser("uninstall")
    uninstall_parser.add_argument("--dest", required=True)
    uninstall_parser.set_defaults(handler=_cmd_uninstall)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
