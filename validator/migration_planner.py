"""Metadata-aware migration planner for ``/spec-migrate``.

# @spec FR-001: Migration planner module
#   - .specs/features/054-migration-planner-penflow-backfill/spec.md#fr-001
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class MigrationPlannerError(ValueError):
    """Raised when migration metadata cannot be parsed safely."""


@dataclass(frozen=True)
class MigrationManifest:
    """Parsed frontmatter for one migration file."""

    version: int
    path: Path
    description: str = ""
    kind: str | None = None
    supersedes: list[int] = field(default_factory=list)
    invalidates_restore_points: list[int] = field(default_factory=list)
    replaces_when_unapplied: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class MigrationPlan:
    """Serializable plan consumed by ``/spec-migrate``."""

    project_version: int
    target_version: int
    apply: list[int]
    skipped: list[dict[str, int | str]]
    invalid_restore_points: list[int]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready representation."""
        return {
            "project_version": self.project_version,
            "target_version": self.target_version,
            "apply": self.apply,
            "skipped": self.skipped,
            "invalid_restore_points": self.invalid_restore_points,
        }


def build_migration_plan(project_dir: Path, livespec_dir: Path) -> MigrationPlan:
    """Compute the migrations that should run for a project.

    Args:
        project_dir: Project root containing ``.specs/livespec-version``.
        livespec_dir: LiveSpec repository root containing ``VERSION`` and
            ``migrations/*/migrate.md``.

    Returns:
        Deterministic migration plan.

    Raises:
        MigrationPlannerError: If versions or frontmatter are invalid.
    """
    project_root = project_dir.resolve()
    repo_root = livespec_dir.resolve()
    project_version = _read_project_version(project_root)
    target_version = _read_target_version(repo_root)
    manifests = load_migration_manifests(repo_root)
    pending = [
        version
        for version in sorted(manifests)
        if project_version < version <= target_version
    ]
    replacements = _pending_replacements(manifests, pending)
    apply = [version for version in pending if version not in replacements]
    skipped = [
        {"version": version, "reason": f"superseded_by_{replacement}"}
        for version, replacement in sorted(replacements.items())
    ]
    invalid_restore_points = sorted(
        {
            restore_point
            for manifest in manifests.values()
            if manifest.version <= target_version
            for restore_point in manifest.invalidates_restore_points
        }
    )
    return MigrationPlan(
        project_version=project_version,
        target_version=target_version,
        apply=apply,
        skipped=skipped,
        invalid_restore_points=invalid_restore_points,
    )


def load_migration_manifests(livespec_dir: Path) -> dict[int, MigrationManifest]:
    """Load every ``migrations/N/migrate.md`` manifest in a LiveSpec repo."""
    migrations_dir = livespec_dir / "migrations"
    if not migrations_dir.is_dir():
        raise MigrationPlannerError(f"migrations directory not found: {migrations_dir}")
    manifests: dict[int, MigrationManifest] = {}
    for path in sorted(migrations_dir.glob("*/migrate.md"), key=_migration_sort_key):
        manifest = _parse_manifest(path)
        if manifest.version in manifests:
            raise MigrationPlannerError(f"duplicate migration version: {manifest.version}")
        manifests[manifest.version] = manifest
    return manifests


def _read_project_version(project_root: Path) -> int:
    path = project_root / ".specs" / "livespec-version"
    if not path.exists():
        return 1
    return _parse_int(path.read_text(encoding="utf-8").strip(), field="project_version")


def _read_target_version(repo_root: Path) -> int:
    path = repo_root / "VERSION"
    if not path.is_file():
        raise MigrationPlannerError(f"VERSION file not found: {path}")
    return _parse_int(path.read_text(encoding="utf-8").strip(), field="target_version")


def _parse_manifest(path: Path) -> MigrationManifest:
    # @spec FR-002: Optional migration metadata fields
    #   - .specs/features/054-migration-planner-penflow-backfill/spec.md#fr-002
    frontmatter = _load_frontmatter(path)
    fallback_version = _parse_int(path.parent.name, field="migration directory")
    version = _parse_int(frontmatter.get("version", fallback_version), field="version")
    if version != fallback_version:
        raise MigrationPlannerError(
            f"{path}: frontmatter version {version} does not match directory {fallback_version}"
        )
    return MigrationManifest(
        version=version,
        path=path,
        description=str(frontmatter.get("description", "")),
        kind=_optional_str(frontmatter.get("kind"), field="kind", path=path),
        supersedes=_int_list(frontmatter.get("supersedes", []), field="supersedes", path=path),
        invalidates_restore_points=_int_list(
            frontmatter.get("invalidates_restore_points", []),
            field="invalidates_restore_points",
            path=path,
        ),
        replaces_when_unapplied=_int_list(
            frontmatter.get("replaces_when_unapplied", []),
            field="replaces_when_unapplied",
            path=path,
        ),
    )


def _load_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    try:
        _, raw, _ = text.split("---", 2)
    except ValueError as exc:
        raise MigrationPlannerError(f"{path}: frontmatter is not closed") from exc
    try:
        parsed = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise MigrationPlannerError(f"{path}: invalid frontmatter YAML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise MigrationPlannerError(f"{path}: frontmatter must be a mapping")
    return parsed


def _pending_replacements(
    manifests: dict[int, MigrationManifest],
    pending: list[int],
) -> dict[int, int]:
    # @spec FR-003: Skip only pending replaced migrations
    # @spec FR-004: Preserve already-applied migration history
    #   - .specs/features/054-migration-planner-penflow-backfill/spec.md#fr-003
    pending_set = set(pending)
    replacements: dict[int, int] = {}
    for replacement_version in pending:
        manifest = manifests[replacement_version]
        for replaced_version in manifest.replaces_when_unapplied:
            if replaced_version in pending_set:
                replacements[replaced_version] = replacement_version
    return replacements


def _int_list(raw: object, *, field: str, path: Path) -> list[int]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise MigrationPlannerError(f"{path}: {field} must be a list of integers")
    values: list[int] = []
    for item in raw:
        if not isinstance(item, int):
            raise MigrationPlannerError(f"{path}: {field} must contain only integers")
        values.append(item)
    return values


def _optional_str(raw: object, *, field: str, path: Path) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise MigrationPlannerError(f"{path}: {field} must be a string")
    return raw


def _parse_int(raw: object, *, field: str) -> int:
    try:
        return int(str(raw).strip())
    except ValueError as exc:
        raise MigrationPlannerError(f"{field} must be an integer: {raw!r}") from exc


def _migration_sort_key(path: Path) -> int:
    return _parse_int(path.parent.name, field="migration directory")


__all__ = [
    "MigrationManifest",
    "MigrationPlan",
    "MigrationPlannerError",
    "build_migration_plan",
    "load_migration_manifests",
]
