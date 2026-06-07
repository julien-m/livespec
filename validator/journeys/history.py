"""History and decision governance for User Journeys v2."""

# @spec FR-009, FR-010, FR-011, FR-012: journey edit history and blocking
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-009

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from .models import JourneyIssue, JourneySeverity


def validate_history(project_root: Path, journey_id: str, source_hash: str) -> list[JourneyIssue]:
    """Validate decision/changelog evidence for changed compiled journeys.

    Args:
        project_root: Project root containing `.specs/`.
        journey_id: Global journey ID.
        source_hash: Current SHA-256 hash of `journey.yaml`.

    Returns:
        Blocking issues when a compiled journey changed without traceability.
    """
    journey_dir = project_root / ".specs" / "journeys" / journey_id
    manifest_path = journey_dir / "compiled" / "manifest.json"
    if not manifest_path.exists():
        return []
    manifest_hash = _manifest_source_hash(manifest_path)
    if manifest_hash is None or manifest_hash == source_hash:
        return []
    changelog_path = journey_dir / "changelog.md"
    decisions_dir = journey_dir / "decisions"
    has_changelog = _file_mentions(changelog_path, source_hash)
    has_decision = (
        any(
            _file_mentions(path, source_hash) and _file_has_classification(path)
            for path in sorted(decisions_dir.glob("*.md"))
        )
        if decisions_dir.exists()
        else False
    )
    if has_changelog and has_decision:
        return []
    return [
        JourneyIssue(
            code="journey_history_missing",
            severity=JourneySeverity.ERROR,
            message=(
                f"Journey {journey_id} changed after compilation; add a decision and "
                "changelog entry with the current source hash."
            ),
            path=journey_dir / "journey.yaml",
        )
    ]


def _manifest_source_hash(path: Path) -> str | None:
    """Read the manifest source hash if the manifest is valid JSON."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    # JSON data is untyped at the boundary; narrow through `object` before checking.
    source_hash = cast(object, data.get("source_hash"))
    return source_hash if isinstance(source_hash, str) and source_hash else None


def _file_mentions(path: Path, value: str) -> bool:
    """Return True when a file exists and contains a required token."""
    if not path.exists():
        return False
    return value in path.read_text(encoding="utf-8", errors="ignore")


def _file_has_classification(path: Path) -> bool:
    """Return True when a decision file declares an accepted classification."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    return any(
        f"classification: {classification}" in text
        for classification in (
            "regression",
            "intentional_update",
            "obsolete",
            "selector_fix",
            "coverage_expansion",
        )
    )


__all__ = ["validate_history"]
