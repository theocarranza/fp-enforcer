## Codex adapter execution

This installed Codex edition adds host-specific guidance on top of the portable FP Enforcer skills.

1. Prefer namespaced skills such as `/fp-enforcer:fp-validate` and `/fp-enforcer:fp-wire`.
2. Hooks resolve via `${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}`.
3. Codex marketplace manifests are written under `.agents/plugins/` (and mirrored paths) by the build.
