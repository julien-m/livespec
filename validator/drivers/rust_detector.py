"""Detect Rust crate dependencies and parse cargo-mutants JSON output."""

# @spec FR-002: Cargo.toml dependency parser using tomllib (no shell grep)
# — .specs/features/021-driver-rust/spec.md#fr-002
# @spec FR-003: cargo-mutants JSON parser exposing caught/missed/timeout/unviable
# — .specs/features/021-driver-rust/spec.md#fr-003
# @spec AC-010: Cargo.toml parsing uses a dedicated parser
# — .specs/features/021-driver-rust/spec.md#ac-010

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any, cast

_DEP_TABLES: tuple[str, ...] = ("dependencies", "dev-dependencies", "build-dependencies")
_MUTANT_OUTCOMES: tuple[str, ...] = ("caught", "missed", "timeout", "unviable")


def _read_cargo_toml(project_root: Path) -> str:
    """Load ``Cargo.toml`` defensively.

    Args:
        project_root: Path to the project root.

    Returns:
        File contents, or an empty string when the file is missing or unreadable.
    """
    cargo_path = project_root / "Cargo.toml"
    if not cargo_path.is_file():
        return ""
    try:
        return cargo_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # Treat unreadable manifests as "feature not detected" so discovery
        # degrades safely instead of crashing on filesystem or encoding issues.
        return ""


def has_cargo_manifest(project_root: str) -> bool:
    """Return ``True`` when ``Cargo.toml`` exists at the project root."""
    return (Path(project_root) / "Cargo.toml").is_file()


def parse_cargo_dependencies(project_root: str) -> list[str]:
    """Parse ``Cargo.toml`` and return declared dependency names.

    Walks the ``[dependencies]``, ``[dev-dependencies]`` and
    ``[build-dependencies]`` tables, capturing both the
    ``dep = "version"`` (string value) and the
    ``dep = { version = "...", features = [...] }`` (table value) syntaxes.

    Args:
        project_root: Path to the project root.

    Returns:
        Lowercased dependency names, deduplicated, in first-seen order. Empty
        when ``Cargo.toml`` is missing, unreadable or contains no dependency
        tables.
    """
    contents = _read_cargo_toml(Path(project_root))
    if not contents:
        return []

    try:
        parsed: dict[str, Any] = tomllib.loads(contents)
    except tomllib.TOMLDecodeError:
        # Invalid TOML is external project input; returning no dependencies keeps
        # capability detection non-fatal for malformed fixtures or repos.
        return []

    seen: set[str] = set()
    ordered: list[str] = []

    for table_name in _DEP_TABLES:
        raw_table = parsed.get(table_name)
        if not isinstance(raw_table, dict):
            continue
        # tomllib returns dict[str, Any]; cast for pyright-strict.
        table = cast(dict[str, Any], raw_table)
        for dep_name in table:
            normalised = dep_name.strip().lower()
            if normalised and normalised not in seen:
                seen.add(normalised)
                ordered.append(normalised)

    return ordered


def has_cargo_dependency(project_root: str, name: str) -> bool:
    """Check whether ``name`` is declared in any Cargo dependency table.

    The match is case-insensitive and exact (crate names are unique tokens; no
    substring match is needed unlike Go module paths).

    Args:
        project_root: Path to the project root.
        name: Dependency name to look up (e.g. ``insta``, ``proptest``).

    Returns:
        ``True`` when the named crate is declared as a dependency.
    """
    needle = name.strip().lower()
    if not needle:
        return False
    return needle in parse_cargo_dependencies(project_root)


def parse_cargo_mutants_json(stdout: str) -> dict[str, int]:
    """Extract mutation counts from ``cargo mutants --json`` output.

    ``cargo mutants --json`` may emit either a single JSON object summarising
    the run, or a stream of JSON objects (one per mutant). This parser handles
    both forms by:
      1. Trying ``json.loads`` on the full stdout (single-object case).
      2. Falling back to line-by-line parsing and aggregating per-mutant
         outcomes by counting the ``outcome`` (or ``status``) field.

    Args:
        stdout: Captured standard output from ``cargo mutants --json``.

    Returns:
        A dictionary with integer counts for ``caught``, ``missed``, ``timeout``
        and ``unviable``. Missing keys default to ``0``. Returns all-zero counts
        when the input cannot be parsed.
    """
    counts: dict[str, int] = {outcome: 0 for outcome in _MUTANT_OUTCOMES}
    text = stdout.strip()
    if not text:
        return counts

    # Form 1 — single JSON object summary (common shape).
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Older cargo-mutants versions may emit line-delimited objects instead of
        # one summary object, so a whole-stdout parse failure is not terminal.
        data = None

    if isinstance(data, dict):
        summary = cast(dict[str, Any], data)
        # Some cargo-mutants versions nest under "outcomes" or "summary".
        candidate = summary
        for nested_key in ("outcomes", "summary"):
            nested = summary.get(nested_key)
            if isinstance(nested, dict):
                candidate = cast(dict[str, Any], nested)
                break
        for outcome in _MUTANT_OUTCOMES:
            value = candidate.get(outcome)
            if isinstance(value, int):
                counts[outcome] = value
            elif isinstance(value, float):
                counts[outcome] = int(value)
        if any(counts[outcome] > 0 for outcome in _MUTANT_OUTCOMES):
            return counts

    # Form 2 — line-delimited JSON, one object per mutant.
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            # Ignore malformed lines so partial JSON streams still yield counts
            # from the valid cargo-mutants events that were emitted.
            continue
        if not isinstance(event, dict):
            continue
        event_dict = cast(dict[str, Any], event)
        outcome_value = event_dict.get("outcome")
        if not isinstance(outcome_value, str):
            outcome_value = event_dict.get("status")
        if isinstance(outcome_value, str):
            normalised = outcome_value.strip().lower()
            if normalised in counts:
                counts[normalised] += 1

    return counts
