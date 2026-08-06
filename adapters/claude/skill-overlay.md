## Claude Code adapter execution

This installed Claude Code edition adds host-specific guidance on top of the portable FP Enforcer skills.

1. Prefer namespaced skills such as `/fp-enforcer:fp-validate` and `/fp-enforcer:fp-wire`.
2. Hooks resolve via `${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}`; Claude continues to expand `CLAUDE_PLUGIN_ROOT`.
3. Host-only skill frontmatter belongs in adapter overlays — keep canonical `skills/*/SKILL.md` portable.
