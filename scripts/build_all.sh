#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

./scripts/validate.sh
python3 adapters/cursor/build_plugin.py
python3 adapters/claude/build_plugin.py
python3 adapters/codex/build_plugin.py
echo "build_all ok"
