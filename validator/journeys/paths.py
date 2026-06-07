"""Filesystem path helpers for journey sources and generated artifacts."""

# @spec FR-002, FR-003, FR-004, FR-007, FR-040: global v2 layout and v1 discovery
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-002

from __future__ import annotations

import re
from pathlib import Path

_NON_IDENTIFIER_RE = re.compile(r"[^0-9A-Za-z]+")


def journey_source_root(project_root: Path) -> Path:
    """Return the root containing canonical journey YAML files."""
    # @spec FR-004: Canonical journey source path
    # — .specs/features/056-executable-user-journeys/spec.md#fr-004
    return project_root / ".specs" / "journeys"


def journey_directory(project_root: Path, journey_id: str) -> Path:
    """Return the canonical v2 directory for a global journey ID."""
    return journey_source_root(project_root) / journey_id


def journey_source_path(project_root: Path, journey_id: str) -> Path:
    """Return the canonical v2 source path for a journey ID."""
    return journey_directory(project_root, journey_id) / "journey.yaml"


def journey_changelog_path(project_root: Path, journey_id: str) -> Path:
    """Return the v2 journey changelog path."""
    return journey_directory(project_root, journey_id) / "changelog.md"


def journey_decisions_dir(project_root: Path, journey_id: str) -> Path:
    """Return the v2 journey decisions directory path."""
    return journey_directory(project_root, journey_id) / "decisions"


def journey_compiled_dir(project_root: Path, journey_id: str) -> Path:
    """Return the v2 journey compiled metadata directory path."""
    return journey_directory(project_root, journey_id) / "compiled"


def journey_manifest_path(project_root: Path, journey_id: str) -> Path:
    """Return the v2 compiled manifest path for a journey."""
    return journey_compiled_dir(project_root, journey_id) / "manifest.json"


def journey_runs_dir(project_root: Path, journey_id: str) -> Path:
    """Return the v2 journey run evidence directory path."""
    return journey_directory(project_root, journey_id) / "runs"


def visual_contracts_dir(project_root: Path, journey_id: str) -> Path:
    """Return the directory containing compiled LLM visual contracts."""
    return journey_compiled_dir(project_root, journey_id) / "visual-contracts"


def feature_backlink_path(project_root: Path, feature: str) -> Path:
    """Return the generated feature-to-journeys backlink path."""
    return project_root / ".specs" / "features" / feature / "journeys.md"


def feature_impact_path(project_root: Path, feature: str) -> Path:
    """Return the generated feature journey-impact history path."""
    return project_root / ".specs" / "features" / feature / "journey-impacts.md"


def iter_journey_source_paths(project_root: Path, journey: str | None = None) -> list[Path]:
    """Return sorted canonical v2 journey source paths."""
    root = journey_source_root(project_root)
    if journey:
        path = journey_source_path(project_root, journey)
        return [path] if path.exists() else []
    return sorted(path for path in root.glob("*/journey.yaml") if path.is_file())


def iter_v1_journey_source_paths(project_root: Path, feature: str | None = None) -> list[Path]:
    """Return sorted legacy v1 `.journey.yaml` sources for migration only."""
    root = journey_source_root(project_root)
    if feature:
        return sorted((root / feature).glob("*.journey.yaml"))
    return sorted(root.glob("*/*.journey.yaml"))


def iter_journey_paths(project_root: Path, feature: str | None = None) -> list[Path]:
    """Return sorted canonical v2 journey source paths.

    Args:
        project_root: Project root containing `.specs/`.
        feature: Deprecated v1 feature filter. Kept for compatibility and
            translated to v2 sources by covered feature in the validator.

    Returns:
        Sorted v2 `journey.yaml` paths.
    """
    if feature:
        return iter_journey_source_paths(project_root)
    return iter_journey_source_paths(project_root)


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
