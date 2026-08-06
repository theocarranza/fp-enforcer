#!/usr/bin/env python3
"""Install and uninstall host adapter plugins. Effects stay in run()."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _build_lib import MARKETPLACE_NAME, PLUGIN_NAME, repo_root

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True)
class Left:
    error: str


@dataclass(frozen=True)
class Right:
    value: A


Either = Left | Right


@dataclass(frozen=True)
class InstallPaths:
    marketplace: Path
    plugin_source: Path
    destination: Path
    record_path: Path
    durable_marketplace: Path | None


@dataclass(frozen=True)
class Plan:
    host: str
    action: str
    paths: InstallPaths
    build_script: Path
    dry_run: bool
    use_cli: bool
    next_steps: tuple[str, ...]


def fold_either(either: Either, on_left: Callable[[str], B], on_right: Callable[[A], B]) -> B:
    match either:
        case Left(error=error):
            return on_left(error)
        case Right(value=value):
            return on_right(value)


def plugin_ref() -> str:
    return f"{PLUGIN_NAME}@{MARKETPLACE_NAME}"


def managed_files(root: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in root.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and not path.name.endswith(".pyc")
        )
    )


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in managed_files(root):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def host_home(host: str, prefix: Path | None) -> Path:
    match (host, prefix):
        case (_, path) if path is not None:
            return path.expanduser().resolve()
        case ("cursor", None):
            return Path(
                os.environ.get("CURSOR_HOME") or Path.home() / ".cursor"
            ).expanduser().resolve()
        case ("claude", None):
            return Path(
                os.environ.get("CLAUDE_HOME") or Path.home() / ".claude"
            ).expanduser().resolve()
        case ("codex", None):
            return Path(
                os.environ.get("CODEX_HOME") or Path.home() / ".codex"
            ).expanduser().resolve()
        case (other, _):
            raise ValueError(f"unsupported host: {other}")


def resolve_paths(host: str, root: Path, prefix: Path | None) -> InstallPaths:
    marketplace = root / "dist" / f"{host}-marketplace"
    plugin_source = marketplace / "plugins" / PLUGIN_NAME
    home = host_home(host, prefix)
    agents_root = (
        prefix.expanduser().resolve()
        if prefix is not None
        else Path(os.environ.get("AGENTS_HOME") or Path.home() / ".agents").expanduser().resolve()
    )
    match host:
        case "cursor":
            local_root = home / "plugins" / "local"
            destination = local_root / PLUGIN_NAME
            return InstallPaths(
                marketplace=marketplace,
                plugin_source=plugin_source,
                destination=destination,
                record_path=local_root / f"{PLUGIN_NAME}-install.json",
                durable_marketplace=None,
            )
        case "claude":
            durable = agents_root / "plugins" / f"{PLUGIN_NAME}-claude-marketplace"
            return InstallPaths(
                marketplace=marketplace,
                plugin_source=plugin_source,
                destination=durable / "plugins" / PLUGIN_NAME,
                record_path=agents_root / "plugins" / f"{PLUGIN_NAME}-claude-install.json",
                durable_marketplace=durable,
            )
        case "codex":
            durable = agents_root / "plugins" / f"{PLUGIN_NAME}-codex-marketplace"
            return InstallPaths(
                marketplace=marketplace,
                plugin_source=plugin_source,
                destination=durable / "plugins" / PLUGIN_NAME,
                record_path=agents_root / "plugins" / f"{PLUGIN_NAME}-codex-install.json",
                durable_marketplace=durable,
            )
        case other:
            raise ValueError(f"unsupported host: {other}")


def next_steps_for(host: str, paths: InstallPaths, *, use_cli: bool, dry_run: bool) -> tuple[str, ...]:
    invoke = f"/{PLUGIN_NAME}:fp-validate"
    prefix = "Dry-run: would install — " if dry_run else ""
    match (host, use_cli):
        case ("cursor", _):
            return (
                f"{prefix}Cursor plugin at {paths.destination}",
                "Restart Cursor or run Developer: Reload Window.",
                f"Then invoke {invoke}",
            )
        case ("claude", True):
            return (
                f"{prefix}Claude marketplace at {paths.durable_marketplace}",
                f"Plugin ref: {plugin_ref()}",
                "Restart Claude Code if the plugin is not listed yet.",
                f"Then invoke {invoke}",
            )
        case ("claude", False):
            return (
                f"{prefix}marketplace at {paths.durable_marketplace}",
                f"/plugin marketplace add {paths.durable_marketplace}",
                f"/plugin install {plugin_ref()}",
                f"Then invoke {invoke}",
            )
        case ("codex", True):
            return (
                f"{prefix}Codex marketplace at {paths.durable_marketplace}",
                f"Plugin ref: {plugin_ref()}",
                "Restart Codex or start a new thread.",
                f"Then invoke {invoke}",
            )
        case ("codex", False):
            return (
                f"{prefix}marketplace at {paths.durable_marketplace}",
                f"codex plugin marketplace add {paths.durable_marketplace}",
                f"codex plugin add {plugin_ref()}",
                f"Then invoke {invoke}",
            )
        case _:
            return (f"Then invoke {invoke}",)


def build_plan(host: str, root: Path, *, dry_run: bool, uninstall: bool, prefix: Path | None) -> Either:
    try:
        paths = resolve_paths(host, root, prefix)
    except ValueError as error:
        return Left(str(error))
    use_cli = prefix is None and host in {"claude", "codex"}
    return Right(
        Plan(
            host=host,
            action="uninstall" if uninstall else "install",
            paths=paths,
            build_script=root / "adapters" / host / "build_plugin.py",
            dry_run=dry_run,
            use_cli=use_cli,
            next_steps=next_steps_for(host, paths, use_cli=use_cli, dry_run=dry_run),
        )
    )


def run_command(command: list[str], *, dry_run: bool) -> Either:
    print("$ " + " ".join(command))
    match dry_run:
        case True:
            return Right(0)
        case False:
            try:
                completed = subprocess.run(command, check=False)
            except FileNotFoundError as error:
                return Left(f"required command unavailable: {error.filename}")
            match completed.returncode:
                case 0:
                    return Right(0)
                case code:
                    return Left(f"command failed ({code}): {' '.join(command)}")


def ensure_built(plan: Plan) -> Either:
    match plan.paths.plugin_source.is_dir():
        case True:
            return Right(plan)
        case False:
            return fold_either(
                run_command([sys.executable, str(plan.build_script)], dry_run=plan.dry_run),
                lambda error: Left(error),
                lambda _code: Right(plan)
                if plan.dry_run or plan.paths.plugin_source.is_dir()
                else Left(f"build did not produce {plan.paths.plugin_source}"),
            )


def write_record(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def copy_tree(source: Path, destination: Path) -> None:
    match destination.exists() or destination.is_symlink():
        case True:
            shutil.rmtree(destination)
        case False:
            pass
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def install_cursor(plan: Plan) -> Either:
    source = plan.paths.plugin_source
    destination = plan.paths.destination
    record_path = plan.paths.record_path
    print(f"Install {source} -> {destination}")
    match plan.dry_run:
        case True:
            return Right(plan)
        case False:
            pass
    match destination.exists() or destination.is_symlink():
        case True if not record_path.is_file():
            return Left(f"refusing to overwrite unmanaged plugin: {destination}")
        case True:
            try:
                record = json.loads(record_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                return Left(f"managed install record unreadable: {error}")
            match record.get("plugin_hash") == tree_hash(destination):
                case True:
                    pass
                case False:
                    return Left(f"managed plugin changed after installation: {destination}")
        case False:
            pass
    copy_tree(source, destination)
    write_record(
        record_path,
        {
            "schema_version": 1,
            "host": "cursor",
            "plugin_name": PLUGIN_NAME,
            "plugin_hash": tree_hash(destination),
            "destination": str(destination),
        },
    )
    return Right(plan)


def install_marketplace_copy(plan: Plan) -> Either:
    durable = plan.paths.durable_marketplace
    match durable:
        case None:
            return Left("durable marketplace path missing")
        case path:
            print(f"Install marketplace {plan.paths.marketplace} -> {path}")
            match plan.dry_run:
                case True:
                    return Right(plan)
                case False:
                    copy_tree(plan.paths.marketplace, path)
                    write_record(
                        plan.paths.record_path,
                        {
                            "schema_version": 1,
                            "host": plan.host,
                            "plugin_name": PLUGIN_NAME,
                            "marketplace_name": MARKETPLACE_NAME,
                            "plugin_ref": plugin_ref(),
                            "destination": str(path),
                            "plugin_hash": tree_hash(path),
                        },
                    )
                    return Right(plan)


def register_claude(plan: Plan) -> Either:
    durable = plan.paths.durable_marketplace
    match durable:
        case None:
            return Left("durable marketplace path missing")
        case path if not plan.use_cli:
            return Right(plan)
        case path:
            return fold_either(
                run_command(["claude", "plugin", "marketplace", "add", str(path)], dry_run=plan.dry_run),
                lambda error: Left(error),
                lambda _code: run_command(
                    ["claude", "plugin", "install", plugin_ref()],
                    dry_run=plan.dry_run,
                ),
            )


def register_codex(plan: Plan) -> Either:
    durable = plan.paths.durable_marketplace
    match durable:
        case None:
            return Left("durable marketplace path missing")
        case path if not plan.use_cli:
            return Right(plan)
        case path:
            return fold_either(
                run_command(["codex", "plugin", "marketplace", "add", str(path)], dry_run=plan.dry_run),
                lambda error: Left(error),
                lambda _code: run_command(
                    ["codex", "plugin", "add", plugin_ref()],
                    dry_run=plan.dry_run,
                ),
            )


def replace_managed(plan: Plan) -> Either:
    """Best-effort removal of a prior managed install so plain install upgrades in one shot."""
    print(f"Replacing any prior managed {plan.host} install…")
    return fold_either(
        uninstall(plan),
        lambda error: Left(error),
        lambda done: Right(done),
    )


def install(plan: Plan) -> Either:
    return fold_either(
        ensure_built(plan),
        lambda error: Left(error),
        lambda built: fold_either(
            replace_managed(built),
            lambda error: Left(error),
            lambda cleared: fold_either(
                {
                    "cursor": install_cursor,
                    "claude": lambda p: fold_either(
                        install_marketplace_copy(p),
                        lambda error: Left(error),
                        lambda ready: fold_either(
                            register_claude(ready),
                            lambda error: Left(error),
                            lambda _code: Right(ready),
                        ),
                    ),
                    "codex": lambda p: fold_either(
                        install_marketplace_copy(p),
                        lambda error: Left(error),
                        lambda ready: fold_either(
                            register_codex(ready),
                            lambda error: Left(error),
                            lambda _code: Right(ready),
                        ),
                    ),
                }[cleared.host](cleared),
                lambda error: Left(error),
                lambda done: Right(done),
            ),
        ),
    )


def read_managed_record(record_path: Path) -> Either:
    match record_path.is_file():
        case False:
            return Left(f"no managed install found at {record_path}")
        case True:
            try:
                return Right(json.loads(record_path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError) as error:
                return Left(f"managed install record unreadable: {error}")


def uninstall_cursor(plan: Plan) -> Either:
    destination = plan.paths.destination
    record_path = plan.paths.record_path
    match record_path.is_file():
        case False:
            print(f"No managed Cursor plugin install found at {record_path}")
            return Right(plan)
        case True:
            return fold_either(
                read_managed_record(record_path),
                lambda error: Left(error),
                lambda record: _remove_cursor(plan, destination, record_path, record),
            )


def _remove_cursor(plan: Plan, destination: Path, record_path: Path, record: dict) -> Either:
    match destination.is_dir():
        case False:
            print(f"Remove stale record {record_path}")
            match plan.dry_run:
                case True:
                    return Right(plan)
                case False:
                    record_path.unlink(missing_ok=True)
                    return Right(plan)
        case True:
            match record.get("plugin_hash") == tree_hash(destination):
                case False:
                    return Left(f"managed plugin changed after installation: {destination}")
                case True:
                    print(f"Remove {destination}")
                    match plan.dry_run:
                        case True:
                            return Right(plan)
                        case False:
                            shutil.rmtree(destination)
                            record_path.unlink(missing_ok=True)
                            return Right(plan)


def uninstall_marketplace(plan: Plan) -> Either:
    durable = plan.paths.durable_marketplace
    record_path = plan.paths.record_path
    match record_path.is_file():
        case False:
            print(f"No managed {plan.host} plugin install found at {record_path}")
            return Right(plan)
        case True:
            return fold_either(
                read_managed_record(record_path),
                lambda error: Left(error),
                lambda record: _remove_marketplace(plan, durable, record_path, record),
            )


def _remove_marketplace(
    plan: Plan,
    durable: Path | None,
    record_path: Path,
    record: dict,
) -> Either:
    target = Path(record.get("destination", durable or ""))
    print(f"Remove {target}")
    match plan.dry_run:
        case True:
            return fold_either(
                _cli_uninstall(plan),
                lambda error: Left(error),
                lambda _code: Right(plan),
            )
        case False:
            match target.exists():
                case True if record.get("plugin_hash") not in (None, tree_hash(target)):
                    return Left(f"managed marketplace changed after installation: {target}")
                case True:
                    shutil.rmtree(target)
                case False:
                    pass
            record_path.unlink(missing_ok=True)
            return fold_either(
                _cli_uninstall(plan),
                lambda error: Left(error),
                lambda _code: Right(plan),
            )


def _cli_uninstall(plan: Plan) -> Either:
    match (plan.host, plan.use_cli):
        case ("claude", True):
            return fold_either(
                run_command(
                    ["claude", "plugin", "uninstall", plugin_ref()],
                    dry_run=plan.dry_run,
                ),
                lambda _error: Right(0),
                lambda code: Right(code),
            )
        case ("codex", True):
            return fold_either(
                run_command(
                    ["codex", "plugin", "remove", plugin_ref()],
                    dry_run=plan.dry_run,
                ),
                lambda _error: Right(0),
                lambda code: Right(code),
            )
        case _:
            return Right(0)


def uninstall(plan: Plan) -> Either:
    match plan.host:
        case "cursor":
            return uninstall_cursor(plan)
        case "claude" | "codex":
            return uninstall_marketplace(plan)
        case other:
            return Left(f"unsupported host: {other}")


def print_next_steps(plan: Plan) -> None:
    for line in plan.next_steps:
        print(line)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Install or uninstall a host adapter plugin. "
            "Plain install replaces any prior managed install of this plugin."
        ),
        epilog=(
            "Examples:\n"
            "  python3 adapters/_install_lib.py --host cursor\n"
            "  python3 adapters/_install_lib.py --host claude --dry-run\n"
            "  python3 adapters/_install_lib.py --host codex --prefix /tmp/plugin-smoke\n"
            "  python3 adapters/_install_lib.py --host claude --uninstall\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--host", choices=("cursor", "claude", "codex"), required=True)
    parser.add_argument("--root", help="Repository root (defaults to template root)")
    parser.add_argument("--prefix", help="Override install root (skips host CLI registration)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove a managed install only (invoked by adapters/<host>/uninstall.sh)",
    )
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve() if args.root else repo_root()
    prefix = Path(args.prefix).expanduser().resolve() if args.prefix else None
    return fold_either(
        build_plan(args.host, root, dry_run=args.dry_run, uninstall=args.uninstall, prefix=prefix),
        lambda error: (print(f"Blocked: {error}", file=sys.stderr) or 2),
        lambda plan: fold_either(
            uninstall(plan) if args.uninstall else install(plan),
            lambda error: (print(f"Blocked: {error}", file=sys.stderr) or 2),
            lambda done: (print_next_steps(done) or 0) if not args.uninstall else (
                print(f"Uninstalled managed {args.host} plugin.") or 0
            ),
        ),
    )


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
