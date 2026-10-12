"""Resolve existing review owners without allocating or inventing feature identity."""

from __future__ import annotations

import re
from pathlib import Path

from validator.identity import SLUG_REGEX, parse_slug

_SHORT_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def _features_root(project_root: Path) -> Path:
    """Require a real feature inventory confined to the canonical project root."""
    root = project_root.resolve(strict=True)
    directory = root / ".specs/features"
    try:
        directory.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError("feature_inventory_missing_or_unconfined") from exc
    if not directory.is_dir():
        raise ValueError("feature_inventory_not_directory")
    return directory


def _confined_feature(directory: Path, candidate: Path) -> Path:
    """Reject feature aliases and escaped or absent directories before source reads."""
    if candidate.is_symlink():
        raise ValueError(f"linked_feature_not_allowed:{candidate.name}")
    try:
        candidate.resolve(strict=True).relative_to(directory.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise ValueError(f"feature_missing_or_unconfined:{candidate.name}") from exc
    if not candidate.is_dir():
        raise ValueError(f"feature_not_directory:{candidate.name}")
    return candidate


# @spec FR-004: Canonical source owner
#   — .specs/features/078-requirement-evidence-integrity/spec.md#fr-004
def resolve_existing_feature(project_root: Path, feature: str) -> Path:
    """Resolve exactly one existing feature, retaining its actual directory identity.

    Args:
        project_root: Project containing the confined feature inventory.
        feature: Explicit numbered slug, or an unambiguous short kebab slug.

    Returns:
        Existing canonical feature directory, never an allocated destination.

    Raises:
        ValueError: Input is invalid, missing, ambiguous, linked or unconfined.
        OSError: The canonical project root or inventory cannot be inspected.

    Side effects:
        Reads directory metadata only; never creates or reads feature files.
    """
    if not (_SHORT_SLUG.fullmatch(feature) or SLUG_REGEX.fullmatch(feature)):
        raise ValueError("invalid_existing_feature_slug")
    directory = _features_root(project_root)
    if SLUG_REGEX.fullmatch(feature):
        return _confined_feature(directory, directory / feature)
    candidates = [
        entry
        for entry in directory.iterdir()
        if (entry.is_dir() or entry.is_symlink())
        and (
            entry.name == feature
            or (SLUG_REGEX.fullmatch(entry.name) and parse_slug(entry.name).name == feature)
        )
    ]
    if len(candidates) != 1:
        reason = "ambiguous" if candidates else "missing"
        raise ValueError(f"existing_feature_{reason}:{feature}")
    return _confined_feature(directory, candidates[0])
