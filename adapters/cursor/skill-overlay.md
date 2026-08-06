## Cursor adapter execution

This installed Cursor edition adds host-specific guidance on top of the portable FP Enforcer skills.

1. Prefer namespaced skills such as `/fp-enforcer:fp-validate` and `/fp-enforcer:fp-wire`.
2. Hooks resolve via `${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` so Open Plugins and Claude hosts both work.
3. Per-project enforcement still uses `fp-enforcer wire` (PyPI runtime); the plugin ships skills and rules.
