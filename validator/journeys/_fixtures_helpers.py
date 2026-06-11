# LiveSpec traceability anchors
# @spec(FR-004)
# @spec(FR-009)

"""Private internals for the fixtures contract: skeleton renderer and scaffold.

Extracted from `fixtures.py` to keep that module within the 300-line
constitution bound; the public API surface remains importable from
`validator.journeys.fixtures` (plan-locked resolution, feature 060).
"""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]  # PyYAML has no typed metadata.
from pydantic import ValidationError

from .paths import fixtures_contract_path, iter_journey_source_paths
from .schema import JourneySourceV2


def render_contract_skeleton(
    fixture_ids: list[str],
    mock_ids: list[str],
    surfaces: list[str],
) -> str:
    """Render a paste-ready fixtures.yaml skeleton for a journey's declared ids.

    Args:
        fixture_ids: Fixture ids declared by the journey.
        mock_ids: Mock ids declared by the journey.
        surfaces: XCUITest surfaces targeted by the journey.

    Returns:
        Minimal valid contract YAML (schema_version 1, every declared id,
        surfaces from journey targets, no screens or markers).
    """
    # @spec FR-004: Paste-ready contract skeleton
    # — .specs/features/060-journey-fixture-bootstrap-contract/spec.md#fr-004
    # Skeleton flow: header line, then one `<id>: surfaces: [...]` entry per
    # declared fixture/mock so the file is valid YAML as-is after pasting.
    surface_list = "[" + ", ".join(sorted(set(surfaces))) + "]"
    lines = ["schema_version: 1"]
    if fixture_ids:
        lines.append("fixtures:")
        for fixture_id in sorted(set(fixture_ids)):
            lines.append(f"  {fixture_id}:")
            lines.append(f"    surfaces: {surface_list}")
    if mock_ids:
        lines.append("mocks:")
        for mock_id in sorted(set(mock_ids)):
            lines.append(f"  {mock_id}:")
            lines.append(f"    surfaces: {surface_list}")
    return "\n".join(lines) + "\n"


def scaffold_fixtures_contract(project_root: Path) -> Path | None:
    """Write a minimal valid contract enumerating existing journey fixtures.

    Enumerates fixture/mock ids across parseable v2 journeys, infers each
    entry's `surfaces` from the union of the referencing journeys' target
    surfaces, and writes a contract without `bootstrap`, `expected_screen`,
    or `required_markers` so compiled output stays wait-free.

    Args:
        project_root: Project root containing `.specs/`.

    Returns:
        The written contract path, or None when the contract already exists
        (idempotent — the existing file is never touched) or when no journey
        declares fixtures or mocks.
    """
    # @spec FR-009: Idempotent fixtures contract scaffold
    # — .specs/features/060-journey-fixture-bootstrap-contract/spec.md#fr-009
    path = fixtures_contract_path(project_root)
    if path.exists():
        return None
    fixture_surfaces: dict[str, set[str]] = {}
    mock_surfaces: dict[str, set[str]] = {}
    for source_path in iter_journey_source_paths(project_root):
        source = _read_journey_source(source_path)
        # Unreadable journeys already fail validation first, so skipping them
        # here cannot let enforcement outrun the scaffold.
        if source is None:
            continue
        surfaces = {target.surface for target in source.targets}
        for fixture_id in source.preconditions.fixtures:
            fixture_surfaces.setdefault(fixture_id, set()).update(surfaces)
        for mock_id in source.preconditions.mocks:
            mock_surfaces.setdefault(mock_id, set()).update(surfaces)
    if not fixture_surfaces and not mock_surfaces:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_scaffold(fixture_surfaces, mock_surfaces), encoding="utf-8")
    return path


def _render_scaffold(
    fixture_surfaces: dict[str, set[str]],
    mock_surfaces: dict[str, set[str]],
) -> str:
    """Render the minimal scaffold YAML with sorted ids and surfaces."""
    lines = ["schema_version: 1"]
    for key, entries in (("fixtures", fixture_surfaces), ("mocks", mock_surfaces)):
        if not entries:
            continue
        lines.append(f"{key}:")
        for entry_id in sorted(entries):
            lines.append(f"  {entry_id}:")
            lines.append("    surfaces: [" + ", ".join(sorted(entries[entry_id])) + "]")
    return "\n".join(lines) + "\n"


def _read_journey_source(path: Path) -> JourneySourceV2 | None:
    """Read one v2 journey source, returning None for any unreadable file."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        return JourneySourceV2.model_validate(data)
    except ValidationError:
        return None


__all__ = [
    "render_contract_skeleton",
    "scaffold_fixtures_contract",
]
