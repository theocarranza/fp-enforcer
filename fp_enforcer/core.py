"""Immutable core types shared across fp-enforcer modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pattern:
    """A single banned-construct detector within a language pack."""

    id: str
    regex: str
    message: str
    rule: str


@dataclass(frozen=True)
class PatternPack:
    """Violation patterns for one language, keyed by file suffix."""

    language: str
    suffixes: tuple[str, ...]
    exclude_suffixes: tuple[str, ...]
    patterns: tuple[Pattern, ...]


@dataclass(frozen=True)
class Violation:
    """One rule violation at a specific location."""

    path: str
    line: int
    pattern_id: str
    message: str
    rule: str
