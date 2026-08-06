# Template-shape migration notes

- Source pattern: agent-continuity + agent-plugin-template
- Version bump: 0.3.0 → 0.3.1
- Skills flattened to `skills/` and mirrored in `fp_enforcer/skills/` for PyPI
- Host adapters under `adapters/{cursor,claude,codex}/` with dedicated uninstall
- `_build_lib.py` ships skills + fp_enforcer package + hooks + assets + `.cursor`
- validate/build/tests green in `/tmp/fp-enforcer-adapt` before workspace sync
