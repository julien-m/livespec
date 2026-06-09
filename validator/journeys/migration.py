# LiveSpec traceability anchors
# @spec(FR-040)

"""Migration from feature-scoped v1 journeys to global v2 journeys."""

# @spec FR-040: migrate v1 feature-scoped journeys to global v2 directories
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-040

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml  # type: ignore[import-untyped]  # PyYAML has no typed metadata.

from .backlinks import render_feature_backlinks
from .models import JourneyIssue, JourneySeverity
from .paths import iter_v1_journey_source_paths, journey_source_path


@dataclass(frozen=True)
class JourneyMigrationResult:
    """Result of a v1 to v2 migration pass."""

    migrated: list[str] = field(default_factory=list)
    issues: list[JourneyIssue] = field(default_factory=list)


def migrate_v1_journeys(project_root: Path, *, apply: bool = False) -> JourneyMigrationResult:
    """Migrate legacy v1 `.journey.yaml` sources to v2 directories."""
    migrated: list[str] = []
    issues: list[JourneyIssue] = []
    for path in iter_v1_journey_source_paths(project_root):
        data = _read_yaml(path)
        if data is None:
            issues.append(_issue("journey_migration_yaml_invalid", "invalid v1 YAML", path))
            continue
        feature = str(data.get("feature", ""))
        feature_spec = project_root / ".specs" / "features" / feature / "spec.md"
        if not feature or not feature_spec.exists():
            issues.append(
                _issue(
                    "journey_migration_feature_missing",
                    f"feature spec missing for legacy journey feature {feature!r}",
                    path,
                )
            )
            continue
        journey_id = str(data.get("id") or path.stem.replace(".journey", ""))
        if apply:
            _write_v2(project_root, journey_id, data)
        migrated.append(journey_id)
    if apply and migrated:
        render_feature_backlinks(project_root)
    return JourneyMigrationResult(migrated=migrated, issues=issues)


def _write_v2(project_root: Path, journey_id: str, data: dict[str, object]) -> None:
    """Write one migrated v2 journey directory."""
    source = journey_source_path(project_root, journey_id)
    source.parent.mkdir(parents=True, exist_ok=True)
    feature = str(data["feature"])
    covers = data.get("covers")
    covers_list = []
    if isinstance(covers, dict):
        for ref in _str_list(covers.get("ac")):
            covers_list.append(
                {
                    "feature": feature,
                    "kind": "ac",
                    "ref": ref,
                    "reason": "Migrated from v1 covers.ac.",
                }
            )
        for ref in _str_list(covers.get("fr")):
            covers_list.append(
                {
                    "feature": feature,
                    "kind": "fr",
                    "ref": ref,
                    "reason": "Migrated from v1 covers.fr.",
                }
            )
    target = data.get("target")
    surface = target.get("surface", "web") if isinstance(target, dict) else "web"
    steps = [{"action": "open", "target": {"route": "/"}}]
    source.write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "id": journey_id,
                "title": str(data.get("title") or journey_id),
                "status": "active",
                "description": f"Migrated v1 journey {journey_id}.",
                "covers": covers_list,
                "run_policy": {"local": str(data.get("run_policy") or "always")},
                "targets": [{"surface": surface, "runner": "playwright"}],
                "steps": steps,
                "privacy": {"llm_allowed": False, "retention": "none"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (source.parent / "changelog.md").write_text(
        "# Changelog\n\n## 2026-06-04 - Migration\n\n- Migrated from v1 journey source.\n",
        encoding="utf-8",
    )
    decisions = source.parent / "decisions"
    decisions.mkdir(exist_ok=True)
    (decisions / "2026-06-04-system-v1-migration.md").write_text(
        "# v1 migration\n\n- classification: coverage_expansion\n- reason: Migrated from v1.\n",
        encoding="utf-8",
    )


def _read_yaml(path: Path) -> dict[str, object] | None:
    """Read a YAML mapping from a legacy journey file."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def _str_list(value: object) -> list[str]:
    """Return string items from a YAML list."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _issue(code: str, message: str, path: Path) -> JourneyIssue:
    """Create a migration issue."""
    return JourneyIssue(code=code, severity=JourneySeverity.ERROR, message=message, path=path)


__all__ = ["JourneyMigrationResult", "migrate_v1_journeys"]
