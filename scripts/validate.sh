#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 - <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(".").resolve()
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
PLUGIN = json.loads((ROOT / ".plugin" / "plugin.json").read_text(encoding="utf-8"))
NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,62}[a-z0-9])?$")
PORTABLE_FM = frozenset({"name", "description", "license"})
REQUIRED_SKILLS = (
    "fp-validate",
    "fp-repair",
    "fp-learn",
    "fp-assimilate",
    "fp-wire",
)


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


match PLUGIN.get("name"):
    case name if isinstance(name, str) and NAME_RE.fullmatch(name) and "--" not in name and ".." not in name:
        pass
    case other:
        fail(f"invalid plugin name: {other!r}")

match PLUGIN.get("version"):
    case version if version == VERSION:
        pass
    case other:
        fail(f".plugin/plugin.json version {other!r} != VERSION {VERSION!r}")

claude = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
match claude.get("version"):
    case version if version == VERSION:
        pass
    case other:
        fail(f".claude-plugin/plugin.json version {other!r} != VERSION {VERSION!r}")

cursor = json.loads((ROOT / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
match cursor.get("version"):
    case version if version == VERSION:
        pass
    case other:
        fail(f".cursor-plugin/plugin.json version {other!r} != VERSION {VERSION!r}")

pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
match f'version = "{VERSION}"' in pyproject:
    case True:
        pass
    case False:
        fail(f"pyproject.toml version is not lockstep with VERSION {VERSION!r}")

plugin_hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
extra_hook_keys = sorted(set(plugin_hooks) - {"description", "hooks"})
match extra_hook_keys:
    case []:
        pass
    case keys:
        fail(f"hooks/hooks.json has unsupported top-level keys: {', '.join(keys)}")

for relative in (
    Path(".claude-plugin") / "marketplace.json",
    Path(".cursor-plugin") / "marketplace.json",
    Path(".agents") / "plugins" / "marketplace.json",
):
    marketplace = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    match marketplace.get("plugins", [{}])[0].get("version"):
        case version if version == VERSION:
            pass
        case other:
            fail(f"{relative.as_posix()} plugin version {other!r} != VERSION {VERSION!r}")
    match marketplace.get("plugins", [{}])[0].get("source"):
        case "./" | "./.":
            pass
        case other:
            fail(f"{relative.as_posix()} plugin source must be './', got {other!r}")

for host in ("cursor", "claude", "codex"):
    manifest = json.loads((ROOT / "adapters" / host / "plugin.template.json").read_text(encoding="utf-8"))
    match (manifest.get("name"), manifest.get("version")):
        case (name, version) if name == PLUGIN["name"] and version == VERSION:
            pass
        case pair:
            fail(f"adapters/{host}/plugin.template.json name/version mismatch: {pair!r}")

skills_root = ROOT / "skills"
skill_dirs = sorted(path for path in skills_root.iterdir() if path.is_dir())
match skill_dirs:
    case []:
        fail("no skills found under skills/")
    case _:
        pass

found = {path.name for path in skill_dirs}
missing = [name for name in REQUIRED_SKILLS if name not in found]
match missing:
    case []:
        pass
    case names:
        fail(f"missing required skills under skills/: {', '.join(names)}")

if "hello" in found:
    fail("template hello skill must not ship in fp-enforcer")

for skill_dir in skill_dirs:
    skill = skill_dir / "SKILL.md"
    match skill.is_file():
        case False:
            fail(f"missing {skill}")
        case True:
            text = skill.read_text(encoding="utf-8")
            match text.startswith("---\n"):
                case False:
                    fail(f"{skill} missing frontmatter")
                case True:
                    end = text.find("\n---", 4)
                    match end:
                        case -1:
                            fail(f"{skill} frontmatter not closed")
                        case _:
                            fm = text[4:end]
                            fields = {}
                            for line in fm.splitlines():
                                match ":" in line:
                                    case True:
                                        key, value = line.split(":", 1)
                                        fields.setdefault(key.strip(), value.strip())
                                    case False:
                                        pass
                            extra = sorted(set(fields) - PORTABLE_FM)
                            match extra:
                                case []:
                                    pass
                                case keys:
                                    fail(
                                        f"{skill}: host-only frontmatter keys not allowed: {', '.join(keys)}"
                                    )
                            match fields.get("name"):
                                case name if name == skill_dir.name:
                                    pass
                                case other:
                                    fail(
                                        f"{skill}: name {other!r} must match directory {skill_dir.name!r}"
                                    )
                            description = fields.get("description", "")
                            match 1 <= len(description) <= 1024:
                                case True:
                                    pass
                                case False:
                                    fail(f"{skill}: description length out of range")
                            # Package copy must stay lockstep for PyPI wheels.
                            pkg = ROOT / "fp_enforcer" / "skills" / skill_dir.name / "SKILL.md"
                            match pkg.is_file() and pkg.read_text(encoding="utf-8") == text:
                                case True:
                                    pass
                                case False:
                                    fail(f"package skill drift: {pkg} must match {skill}")

for required in (
    ROOT / "hooks" / "hooks.json",
    ROOT / "fp_enforcer" / "__main__.py",
    ROOT / "fp_enforcer" / "rules" / "manifest.json",
    ROOT / "pyproject.toml",
    ROOT / "adapters" / "_build_lib.py",
    ROOT / "adapters" / "_install_lib.py",
    ROOT / "adapters" / "_install_lib.sh",
    ROOT / "adapters" / "_uninstall_lib.sh",
):
    match required.is_file():
        case True:
            pass
        case False:
            fail(f"missing required product file: {required}")

print(f"validate ok: {PLUGIN['name']}@{VERSION} ({len(skill_dirs)} skills)")
PY

if command -v skills-ref >/dev/null 2>&1; then
  for skill in skills/*/SKILL.md; do
    skills-ref validate "$(dirname "$skill")"
  done
else
  echo "skills-ref not installed; skipped skill-spec CLI validation"
fi
