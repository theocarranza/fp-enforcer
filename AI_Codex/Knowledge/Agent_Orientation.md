---
type: orientation
tags: [knowledge, orientation]
created: 2026-08-09
---

# Agent Orientation — fp-enforcer

Entry point for agents working in this vault. Start here, then open the newest note under `Agent_Sessions/`.

## Knowledge Index

- [[Agent Orientation]] — this note
- Vault map: [[../README]]

## Slash commands

| Command | Purpose |
| --- | --- |
| `/agent-continuity:init-workspace` | Scaffold the CLAUDE.md tree. |
| `/agent-continuity:init-vault` | Scaffold this vault skeleton. |
| `/agent-continuity:init-rules` | Drop starter `.agent/rules/*.md` templates. |
| `/agent-continuity:mine-bases` | Backfill frontmatter + Base dashboards (software-project). |
| `/agent-continuity:query-vault` | Read-only live query of the vault via the Obsidian CLI. |
| `/agent-continuity:canvas-map` | Generate an Architecture Canvas relationship map. |
| `/agent-continuity:research-ingest` | Ingest a URL into a source-stamped reference note. |
| `/agent-continuity:vault-lint` | Audit the vault against its archetype spec. |

## Conventions

- Ticket **status** = folder under `Tickets/` (never a frontmatter `status` field).
- Session filenames: `YYYY-MM-DD-HHMMSS-kebab-slug`.
- Prefer Base queries over bulk-reading vault markdown when Obsidian is open.
