"""Antigravity hook payload and response adapters."""

from __future__ import annotations


def _path_from_mapping(mapping: dict[str, object], *keys: str) -> str | None:
    for key in keys:
        match mapping.get(key):
            case str() as candidate if candidate:
                return candidate
            case _:
                pass
    return None


def extract_path(payload: dict) -> str | None:
    match payload.get("arguments"):
        case dict() as arguments:
            match _path_from_mapping(
                arguments, "path", "file", "AbsolutePath", "TargetFile"
            ):
                case str() as path:
                    return path
                case _:
                    pass
        case _:
            pass
    match payload.get("tool_input"):
        case dict() as tool_input:
            return _path_from_mapping(tool_input, "path", "file_path")
        case _:
            return None


def format_edit(message: str | None) -> dict:
    match message:
        case str() as text if text:
            return {"decision": "block", "reason": text}
        case _:
            return {}


def format_stop(message: str | None) -> dict:
    match message:
        case str() as text if text:
            return {"decision": "block", "reason": text}
        case _:
            return {}
