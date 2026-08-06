#!/usr/bin/env python3
"""Pure packaging helpers for host adapters. Side effects stay in run_build()."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar

A = TypeVar("A")
B = TypeVar("B")

PLUGIN_NAME = "fp-enforcer"
MARKETPLACE_NAME = "fp-enforcer-local"
FIXED_ZIP_TIME = (2026, 8, 6, 0, 0, 0)
IGNORE_NAMES = frozenset({"__pycache__", ".git", "dist", "adapters", ".github"})
AUTHORING_SCRIPTS = frozenset({"validate.sh", "build_all.sh"})
OVERLAY_SKILL = "fp-validate"
SHIPPED_TREES = (
    "skills",
    "hooks",
    "assets",
    "fp_enforcer",
)
# Extra authoring trees shipped into the plugin payload (Cursor rules for alwaysApply).
SHIPPED_DOT_TREES = (".cursor",)


@dataclass(frozen=True)
class Left:
    error: str


@dataclass(frozen=True)
class Right:
    value: A


Either = Left | Right


def fold(either: Either, on_left: Callable[[str], B], on_right: Callable[[A], B]) -> B:
    match either:
        case Left(error=error):
            return on_left(error)
        case Right(value=value):
            return on_right(value)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_version(root: Path) -> Either:
    path = root / "VERSION"
    match path.is_file():
        case False:
            return Left(f"missing VERSION at {path}")
        case True:
            return Right(path.read_text(encoding="utf-8").strip())


def load_json(path: Path) -> Either:
    match path.is_file():
        case False:
            return Left(f"missing json file: {path}")
        case True:
            return Right(json.loads(path.read_text(encoding="utf-8")))


def ensure_version_lockstep(manifest: dict, version: str) -> Either:
    match (manifest.get("name"), manifest.get("version")):
        case (PLUGIN_NAME, locked) if locked == version:
            return Right(manifest)
        case (name, locked):
            return Left(
                f"plugin template name/version mismatch: "
                f"expected ({PLUGIN_NAME!r}, {version!r}), got ({name!r}, {locked!r})"
            )


def inject_overlay(skill_text: str, overlay: str) -> Either:
    match skill_text.startswith("---\n"):
        case False:
            return Left("canonical SKILL.md does not start with YAML frontmatter")
        case True:
            end = skill_text.find("\n---", 4)
            match end:
                case -1:
                    return Left("canonical SKILL.md frontmatter is not closed")
                case _:
                    split_at = end + len("\n---")
                    body = skill_text[split_at:].lstrip("\n")
                    return Right(skill_text[:split_at] + "\n\n" + overlay.strip() + "\n\n" + body)


def ignore_copy(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in IGNORE_NAMES or name.endswith(".pyc") or name == ".gitkeep"
    }


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def file_digest_map(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(item for item in root.rglob("*") if item.is_file())
        if path.name != "BUILD-MANIFEST.json"
    }


def marketplace_document(version: str, description: str) -> dict:
    return {
        "name": MARKETPLACE_NAME,
        "owner": {"name": "monolith", "url": "https://github.com/theocarranza"},
        "metadata": {"description": "Local marketplace for FP Enforcer"},
        "plugins": [
            {
                "name": PLUGIN_NAME,
                "source": f"./plugins/{PLUGIN_NAME}/",
                "description": description,
                "version": version,
            }
        ],
    }


def marketplace_manifest_paths(output: Path, host_plugin_dir: str) -> tuple[Path, ...]:
    """Codex accepts `.agents/plugins/`, `.claude-plugin/`, `.cursor-plugin/` — not `.codex-plugin/`."""
    match host_plugin_dir:
        case ".codex-plugin":
            return (
                output / ".agents" / "plugins" / "marketplace.json",
                output / ".claude-plugin" / "marketplace.json",
                output / host_plugin_dir / "marketplace.json",
            )
        case _:
            return (output / host_plugin_dir / "marketplace.json",)


def copy_component_tree(source: Path, destination: Path) -> None:
    match source.exists():
        case True:
            shutil.copytree(source, destination, dirs_exist_ok=True, ignore=ignore_copy)
        case False:
            return None


def materialize_plugin(
    *,
    output: Path,
    host_plugin_dir: str,
    adapter_root: Path,
    overlay_path: Path,
    manifest: dict,
) -> Either:
    root = repo_root()
    plugin_root = output / "plugins" / PLUGIN_NAME
    skills_root = root / "skills"
    overlay_skill = skills_root / OVERLAY_SKILL / "SKILL.md"
    required_skills = (
        "fp-validate",
        "fp-repair",
        "fp-learn",
        "fp-assimilate",
        "fp-wire",
    )
    match skills_root.is_dir():
        case False:
            return Left(f"missing skills directory: {skills_root}")
        case True:
            missing = tuple(
                name for name in required_skills if not (skills_root / name / "SKILL.md").is_file()
            )
            match missing:
                case ():
                    pass
                case names:
                    return Left(f"missing required skills: {', '.join(names)}")
            match overlay_skill.is_file():
                case False:
                    return Left(f"missing overlay skill: {overlay_skill}")
                case True:
                    match output.exists():
                        case True:
                            shutil.rmtree(output)
                        case False:
                            pass
                    for name in SHIPPED_TREES:
                        copy_component_tree(root / name, plugin_root / name)
                    for name in SHIPPED_DOT_TREES:
                        copy_component_tree(root / name, plugin_root / name)
                    return fold(
                        inject_overlay(
                            overlay_skill.read_text(encoding="utf-8"),
                            overlay_path.read_text(encoding="utf-8"),
                        ),
                        lambda error: Left(error),
                        lambda text: _finish_materialize(
                            overlay_text=text,
                            root=root,
                            plugin_root=plugin_root,
                            output=output,
                            host_plugin_dir=host_plugin_dir,
                            adapter_root=adapter_root,
                            manifest=manifest,
                        ),
                    )


def _finish_materialize(
    *,
    overlay_text: str,
    root: Path,
    plugin_root: Path,
    output: Path,
    host_plugin_dir: str,
    adapter_root: Path,
    manifest: dict,
) -> Either:
    overlay_dest = plugin_root / "skills" / OVERLAY_SKILL / "SKILL.md"
    overlay_dest.write_text(overlay_text, encoding="utf-8")
    scripts_src = root / "scripts"
    match scripts_src.is_dir():
        case True:
            scripts_dst = plugin_root / "scripts"
            scripts_dst.mkdir(parents=True, exist_ok=True)
            for path in sorted(scripts_src.iterdir()):
                match path.is_file() and path.name not in AUTHORING_SCRIPTS:
                    case True:
                        shutil.copy2(path, scripts_dst / path.name)
                    case False:
                        pass
        case False:
            pass
    match (root / ".mcp.json").is_file():
        case True:
            shutil.copy2(root / ".mcp.json", plugin_root / ".mcp.json")
        case False:
            pass
    # Ship pyproject for local editable installs from the plugin payload.
    match (root / "pyproject.toml").is_file():
        case True:
            shutil.copy2(root / "pyproject.toml", plugin_root / "pyproject.toml")
        case False:
            pass
    open_plugin = root / ".plugin" / "plugin.json"
    match open_plugin.is_file():
        case True:
            write_json(
                plugin_root / ".plugin" / "plugin.json",
                json.loads(open_plugin.read_text(encoding="utf-8")),
            )
        case False:
            pass
    write_json(plugin_root / host_plugin_dir / "plugin.json", manifest)
    adapter_agents = adapter_root / "agents"
    match adapter_agents.is_dir():
        case True:
            copy_component_tree(adapter_agents, plugin_root / "agents")
        case False:
            pass
    description = str(manifest.get("description", PLUGIN_NAME))
    version = str(manifest["version"])
    marketplace = marketplace_document(version, description)
    for path in marketplace_manifest_paths(output, host_plugin_dir):
        write_json(path, marketplace)
    adapter_readme = adapter_root / "README.md"
    match adapter_readme.is_file():
        case True:
            shutil.copy2(adapter_readme, output / "README.md")
        case False:
            pass
    write_json(
        output / "BUILD-MANIFEST.json",
        {"schema_version": 1, "files": file_digest_map(output)},
    )
    return Right(output)


def write_zip(marketplace_root: Path, zip_path: Path, archive_root_name: str) -> Path:
    zip_path = zip_path.resolve()
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=zip_path.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(item for item in marketplace_root.rglob("*") if item.is_file()):
                relative = Path(archive_root_name) / path.relative_to(marketplace_root)
                info = zipfile.ZipInfo(relative.as_posix(), FIXED_ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
    finally:
        temporary.replace(zip_path)
    return zip_path


def run_build(
    *,
    host: str,
    host_plugin_dir: str,
    adapter_root: Path,
    output: Path,
    zip_path: Path | None,
) -> Either:
    root = repo_root()
    return fold(
        read_version(root),
        lambda error: Left(error),
        lambda version: fold(
            load_json(adapter_root / "plugin.template.json"),
            lambda error: Left(error),
            lambda manifest: fold(
                ensure_version_lockstep(manifest, version),
                lambda error: Left(error),
                lambda locked: fold(
                    materialize_plugin(
                        output=output,
                        host_plugin_dir=host_plugin_dir,
                        adapter_root=adapter_root,
                        overlay_path=adapter_root / "skill-overlay.md",
                        manifest=locked,
                    ),
                    lambda error: Left(error),
                    lambda built: Right(
                        {
                            "host": host,
                            "output": built,
                            "zip": None
                            if zip_path is None
                            else write_zip(built, zip_path, f"{host}-marketplace"),
                        }
                    ),
                ),
            ),
        ),
    )
