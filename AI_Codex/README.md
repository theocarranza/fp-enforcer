# AI_Codex — fp-enforcer

Agent Continuity vault for **fp-enforcer** (`software-project` archetype).

Status for tickets is encoded by folder (`Tickets/Active|Ready|Closed|Resolved`).
Identity and classification live in frontmatter — see [[Knowledge/Agent_Orientation]].

## Taxonomy

- **Knowledge/** — Permanent distilled knowledge notes (patterns, domains, references) + the knowledge MOC
- **Tickets/Active/** — In-flight ticket ledgers
- **Tickets/Ready/** — Groomed, ready-to-start tickets
- **Tickets/Closed/** — Merged/closed, awaiting release
- **Tickets/Resolved/** — Shipped/archived ticket ledgers
- **Features/** — Feature specifications and implementation detail
- **Architecture/** — High-level architecture overviews (subfolders below for ADRs/patterns/etc.)
- **Architecture/ADR/** — Architecture Decision Records
- **Architecture/Patterns/** — Recurring design patterns
- **Architecture/Infrastructure/** — Structural/infra definitions
- **Architecture/Agent-Governance/** — Agent governance protocols and directives
- **Architecture/Protocols/** — Operational protocols
- **Agent_Sessions/** — Operational journal of agent sessions (doubly-linked chain)
- **Agent_Reports/** — Formal agent-generated reports
- **assets/** — Images and binary attachments
- **Meta/** — Templates, scripts, and vault plumbing

## Dashboards

- `Tickets.base` — ticket board by status lane
- `Features.base` — features by area
- `Agent_Sessions.base` — session journal

## Marker

`.agent-continuity-vault.json` records `type=software-project` so enforcement hooks and `vault-lint` share one spec.
