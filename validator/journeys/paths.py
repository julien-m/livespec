# LiveSpec traceability anchors
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-004)
# @spec(FR-007)
# @spec(FR-040)

"""Filesystem path helpers for journey sources and generated artifacts."""

# @spec FR-002, FR-003, FR-004, FR-007, FR-040: global v2 layout and v1 discovery
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-002

from __future__ import annotations

import re
from pathlib import Path

import yaml

from ..exceptions import XcuitestTargetUnresolvedError

_NON_IDENTIFIER_RE = re.compile(r"[^0-9A-Za-z]+")


def journey_source_root(project_root: Path) -> Path:
    """Return the root containing canonical journey YAML files."""
    # @spec FR-004: Canonical journey source path
    # — .specs/features/056-executable-user-journeys/spec.md#fr-004
    return project_root / ".specs" / "journeys"


def fixtures_contract_path(project_root: Path) -> Path:
    """Return the project-local journey fixtures contract path."""
    # @spec FR-001: fixtures_contract_path helper
    # — .specs/features/060-journey-fixture-bootstrap-contract/spec.md#fr-001
    return journey_source_root(project_root) / "fixtures.yaml"


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


def resolve_xcuitest_target_dir(project_root: Path, surface: str) -> Path:
    """Return the XCUITest target directory that receives generated journeys.

    An explicit ``testDir`` on the matching ``runner: xcuitest`` surface of
    ``.specs/surfaces.yaml`` (matched by ``platform``) wins. Otherwise the
    project's unique top-level ``*UITests`` directory is used: for ``ios`` the
    one without ``watch`` in its name, for ``watchos`` the one with it
    (case-insensitive). No project name is hardcoded.

    Args:
        project_root: Project root containing ``.specs/``.
        surface: ``ios`` or ``watchos``.

    Returns:
        The target directory; artifacts go under its ``Journeys/`` subdirectory.

    Raises:
        XcuitestTargetUnresolvedError: When zero or several directories match.
    """
    # @spec FR-007, AC-006, AC-007: project-resolved XCUITest destination
    # — .specs/features/056-executable-user-journeys/spec.md#fr-007
    override = _surfaces_test_dir(project_root, surface)
    if override is not None:
        return project_root / override
    wants_watch = surface == "watchos"
    candidates = sorted(
        path.name
        for path in project_root.glob("*UITests")
        if path.is_dir() and ("watch" in path.name.lower()) == wants_watch
    )
    if len(candidates) != 1:
        raise XcuitestTargetUnresolvedError(surface, candidates)
    return project_root / candidates[0]


def _surfaces_test_dir(project_root: Path, surface: str) -> str | None:
    """Return the declared ``testDir`` of the xcuitest surface for ``surface``."""
    surfaces_path = project_root / ".specs" / "surfaces.yaml"
    if not surfaces_path.is_file():
        return None
    try:
        parsed: object = yaml.safe_load(surfaces_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    raw = parsed.get("surfaces") if isinstance(parsed, dict) else None
    entries: list[object] = raw if isinstance(raw, list) else []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        runner = str(entry.get("runner", "")).lower()
        platform = str(entry.get("platform", "")).lower()
        test_dir = entry.get("testDir")
        if runner == "xcuitest" and platform == surface and isinstance(test_dir, str):
            stripped = test_dir.strip()
            if stripped:
                return stripped
    return None


def relative_to_project(project_root: Path, path: Path) -> str:
    """Return a project-relative path when possible."""
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
