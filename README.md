# fp-enforcer

![Version](https://img.shields.io/badge/version-0.3.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-stdlib%20only-success)
![Tests](https://img.shields.io/badge/tests-78%20passing-brightgreen)
![Paradigm](https://img.shields.io/badge/paradigm-functional-8A2BE2)
![Changelog](https://img.shields.io/badge/changelog-keep%20a%20changelog-E05735)

Real-time enforcement of the functional programming paradigm for agent-driven
codebases. fp-enforcer ships a canonical rule set, a violation scanner, agent
hooks, and skills that let coding agents **enforce**, **validate**, **repair**,
and **learn** functional programming discipline on any project.

## Install

Install the runtime once per machine from PyPI:

```bash
pipx install fp-enforcer
# or: uv tool install fp-enforcer
```

Then wire it into a project:

```bash
fp-enforcer wire --client cursor --dest /path/to/project
fp-enforcer wire --client all --dest /path/to/project
fp-enforcer unwire --dest /path/to/project
```

Update is a two-step remote refresh:

```bash
pipx upgrade fp-enforcer
fp-enforcer wire --client all --dest /path/to/project
```

### Marketplace installs (agent-facing layer)

- **Claude Code**: `/plugin marketplace add theocarranza/fp-enforcer`, then
  `/plugin install fp-enforcer@fp-enforcer`.
- **Codex**: `codex plugin marketplace add theocarranza/fp-enforcer`, then
  `codex plugin add fp-enforcer@fp-enforcer`.
- **Cursor**: via the Cursor Marketplace (pending listing).

Marketplace plugins deliver the skills and rules; the `fp-wire` skill then
installs the runtime from PyPI and wires the project (hooks included).

## What it does

| Capability | Mechanism |
| --- | --- |
| Enforce | Vendor hooks (post-edit and completion gates) inject violation reports into the agent loop in real time. |
| Validate | `fp-enforcer validate` lints files, unified diffs, or entire trees against machine-readable pattern packs. |
| Repair | The `fp-repair` skill converts a validation report into an ordered, rule-linked fix procedure the agent executes. |
| Learn | `fp-enforcer learn` detects FP libraries in a project (dartz, fpdart, rxdart, fp-ts, ...) and generates agent-facing knowledge profiles. |
| Assimilate | `fp-enforcer assimilate` activates curated library/language-feature pattern packs detected in the project, gated by embedded self-tests. |

## Design

- **Generic sources, vendor adapters.** Rules (`fp_enforcer/rules/`), pattern
  packs (`fp_enforcer/rules/patterns/`), and the Python core are vendor-neutral
  and ship inside the PyPI package. `wire` renders the vendor-specific harness
  (Cursor, Claude, Codex, Antigravity) into the *target project*. Nothing is
  ever written to host-global folders.
- **Stdlib only.** The runtime is Python 3.10+ standard library, written in the
  functional style the product enforces: frozen dataclasses, pure functions,
  pattern matching, effects at the edges.
- **Skills follow the [Agent Skills](https://agentskills.io/specification)
  open standard**; marketplace manifests are optional adapters (Claude Code,
  Codex, Cursor) on top of the PyPI distribution.

## Wiring a project

`fp-enforcer wire`:

1. Vendors the runtime into `<dest>/.fp-enforcer/` (package, rules, launcher).
2. Renders rules for the client (`.cursor/rules/*.mdc`, `.agent/rules/*.md`, ...).
3. Merges hook wiring **non-destructively** into existing `hooks.json` /
   `settings.json` files (existing entries are preserved; ours are tagged by
   the `.fp-enforcer/run_hook.py` command and are idempotent).
4. Records everything in `<dest>/.fp-enforcer/install_manifest.json` so
   `unwire` reverses only what was installed.

## Validate and learn

```bash
# Scan paths (files or directories)
fp-enforcer validate path/to/lib

# Scan only the added lines of a diff
git diff | fp-enforcer validate --diff -

# Generate FP library knowledge profiles for agents
fp-enforcer learn --dest /path/to/project

# Activate curated pattern packs for detected FP libraries/features
fp-enforcer assimilate --dest /path/to/project
```

### Suppressing a justified exception

Tripwire patterns can over-fire on constructs the rules themselves permit
(e.g. `CompositeSubscription.add`, edge throws). Waive a pattern inline with a
directive naming the pattern ids — on the violating line or the comment line
directly above it:

```dart
// fp-allow: no-collection-mutation — disposal binding, fp-rxdart memory 1
composite.add(subscription);
```

Every suppression is grep-able (`grep -r "fp-allow"`), keeping exceptions
explicit and auditable, as fp-core requires.

## Layout

```
fp_enforcer/           python stdlib core: validate, hook_runtime, adapters, learn, install
fp_enforcer/rules/     canonical rule set (vendor-neutral markdown + manifest.json)
fp_enforcer/rules/patterns/  machine-readable violation patterns per language
fp_enforcer/skills/    fp-validate, fp-repair, fp-learn, fp-assimilate, fp-wire (SKILL.md)
hooks/hooks.json       plugin-level hook wiring template
tests/                 stdlib unittest suite
.github/workflows/     CI + tag-triggered PyPI release (trusted publishing)
```

## Development

Run from a checkout without installing:

```bash
python3 -m unittest discover -s tests -v
python3 -m fp_enforcer validate .        # module form works from the repo root
```

The repository dogfoods itself: its own `.cursor/` harness is generated by its
own installer.
