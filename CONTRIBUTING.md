# Contributing

1. Keep `VERSION`, `.plugin/plugin.json`, host manifests, adapter `plugin.template.json`, and `pyproject.toml` in lockstep.
2. Canonical skills live under `skills/<name>/SKILL.md` with portable frontmatter only (`name`, `description`, `license`). Mirror the same files under `fp_enforcer/skills/` for PyPI package data.
3. Host-only guidance goes in `adapters/<host>/skill-overlay.md` — never mutate canonical skills with host fields.
4. Run `./scripts/validate.sh` then `./scripts/build_all.sh` before opening a PR.
5. Do not hand-edit `dist/`.
