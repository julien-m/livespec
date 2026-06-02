"""Filesystem path helpers for journey sources and generated artifacts."""

from __future__ import annotations

import re
from pathlib import Path

_NON_IDENTIFIER_RE = re.compile(r"[^0-9A-Za-z]+")


def journey_source_root(project_root: Path) -> Path:
    """Return the root containing canonical journey YAML files."""
    # @spec FR-004: Canonical journey source path
    # — .specs/features/056-executable-user-journeys/spec.md#fr-004
    return project_root / ".specs" / "journeys"


def iter_journey_paths(project_root: Path, feature: str | None = None) -> list[Path]:
    """Return sorted journey source paths.

    Args:
        project_root: Project root containing `.specs/`.
        feature: Optional feature slug to scope the scan.

    Returns:
        Sorted `.journey.yaml` paths.
    """
    root = journey_source_root(project_root)
    if feature:
        return sorted((root / feature).glob("*.journey.yaml"))
    return sorted(root.glob("*/*.journey.yaml"))


def slug_to_snake(value: str) -> str:
    """Convert a journey id into a stable snake_case filename stem."""
    cleaned = _NON_IDENTIFIER_RE.sub("_", value).strip("_").lower()
    return cleaned or "journey"


def slug_to_pascal(value: str) -> str:
    """Convert a journey id into a stable PascalCase class stem."""
    return "".join(part.capitalize() for part in slug_to_snake(value).split("_")) or "Journey"


def compiled_artifact_path(project_root: Path, feature: str, journey_id: str, surface: str) -> Path:
    """Return the native artifact destination for a journey target surface."""
    stem = slug_to_snake(journey_id)
    if surface == "web":
        return project_root / "tests" / "e2e" / "journeys" / feature / f"{stem}.spec.ts"
    if surface in {"ios", "watchos"}:
        return (
            project_root
            / "STRAPTUITests"
            / "Journeys"
            / f"{slug_to_pascal(journey_id)}Journey.swift"
        )
    if surface in {"android", "maestro"}:
        return project_root / ".specs" / "maestro" / "journeys" / feature / f"{stem}.yaml"
    return project_root / ".specs" / "journeys" / ".compiled" / feature / f"{stem}.{surface}.txt"


def relative_to_project(project_root: Path, path: Path) -> str:
    """Return a project-relative path when possible."""
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
