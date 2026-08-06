#!/usr/bin/env python3
"""Build a reproducible Codex marketplace from the portable plugin core."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _build_lib import fold, repo_root, run_build

HOST = "codex"
HOST_PLUGIN_DIR = ".codex-plugin"


def parse_args() -> argparse.Namespace:
    root = repo_root()
    version = Path(root / "VERSION").read_text(encoding="utf-8").strip()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(root / "dist" / "codex-marketplace"))
    parser.add_argument(
        "--zip",
        dest="zip_path",
        default=str(root / "dist" / f"fp-enforcer-codex-{version}.zip"),
    )
    parser.add_argument("--no-zip", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_build(
        host=HOST,
        host_plugin_dir=HOST_PLUGIN_DIR,
        adapter_root=Path(__file__).resolve().parent,
        output=Path(args.output),
        zip_path=None if args.no_zip else Path(args.zip_path),
    )
    return fold(
        result,
        lambda error: (print(error, file=sys.stderr) or 1),
        lambda payload: (
            print(f"Built Codex marketplace: {payload['output']}")
            or (
                0
                if payload["zip"] is None
                else (print(f"Built Codex release: {payload['zip']}") or 0)
            )
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
