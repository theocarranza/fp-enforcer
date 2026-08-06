# Host adapters

Build and install host-specific marketplaces for Cursor, Claude Code, and Codex.

- `adapters/<host>/build_plugin.py` — materialize `dist/<host>-marketplace/`
- `adapters/<host>/install.sh` — one-command install / upgrade (curl one-liner supported)
- `adapters/<host>/uninstall.sh` — dedicated uninstall (no `--uninstall` on install)

Shared libraries: `_build_lib.py`, `_install_lib.py`, `_install_lib.sh`, `_uninstall_lib.sh`.
