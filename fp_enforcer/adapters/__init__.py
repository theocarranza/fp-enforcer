"""Vendor-specific hook payload and response adapters."""

from __future__ import annotations

from fp_enforcer.adapters import antigravity, claude, codex, cursor


def by_name(client: str):
    match client:
        case "cursor":
            return cursor
        case "claude":
            return claude
        case "codex":
            return codex
        case "antigravity":
            return antigravity
        case _:
            raise ValueError(f"unknown client: {client!r}")
