"""Compiled-only execution planner for User Journeys v2."""

# @spec FR-024, FR-027: compiled-only journey execution and stage run policies
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-024

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml  # type: ignore[import-untyped]  # PyYAML has no typed metadata.
from pydantic import ValidationError

from .manifest import read_compiled_manifest
from .models import JourneyIssue, JourneySeverity
from .paths import iter_journey_source_paths
from .schema import JourneySourceV2, RunPolicyValue, RunStage


@dataclass(frozen=True)
class JourneyRunResult:
    """Result summary for a compiled-only journey run selection."""

    executed: list[str] = field(default_factory=list)
    manual: list[str] = field(default_factory=list)
    disabled: list[str] = field(default_factory=list)
    issues: list[JourneyIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        """Return the number of blocking run issues."""
        return sum(1 for issue in self.issues if issue.severity is JourneySeverity.ERROR)


def run_journeys(
    project_root: Path,
    *,
    journey: str | None = None,
    feature: str | None = None,
    stage: RunStage = RunStage.LOCAL,
    execute: bool = True,
) -> JourneyRunResult:
    """Select and run already compiled journeys without compiling."""
    executed: list[str] = []
    manual: list[str] = []
    disabled: list[str] = []
    issues: list[JourneyIssue] = []
    for source_path in iter_journey_source_paths(project_root):
        source, raw_text = _read_source(source_path)
        if source is None or raw_text is None:
            continue
        if journey is not None and source.id != journey:
            continue
        covered_features = {cover.feature for cover in source.covers}
        if feature is not None and feature not in covered_features:
            continue
        policy = source.run_policy.get(stage, RunPolicyValue.IMPACTED)
        if policy is RunPolicyValue.DISABLED or source.status.value == "disabled":
            disabled.append(source.id)
            continue
        if policy is RunPolicyValue.MANUAL or source.status.value == "manual":
            manual.append(source.id)
            continue
        manifest = read_compiled_manifest(project_root, source.id)
        current_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        if manifest is None:
            issues.append(
                _issue("journey_compiled_missing", "compiled manifest is missing", source_path)
            )
            continue
        if manifest.source_hash != current_hash:
            issues.append(
                _issue(
                    "journey_compiled_stale",
                    "compiled manifest source hash is stale",
                    source_path,
                )
            )
            continue
        if execute:
            # Native process execution is delegated to the project runner by CLI integration.
            pass
        executed.append(source.id)
    return JourneyRunResult(executed=executed, manual=manual, disabled=disabled, issues=issues)


def _read_source(path: Path) -> tuple[JourneySourceV2 | None, str | None]:
    """Read a v2 journey source for run selection."""
    try:
        raw_text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw_text)
        if not isinstance(data, dict):
            return None, raw_text
        return JourneySourceV2.model_validate(data), raw_text
    except (OSError, yaml.YAMLError, ValidationError):
        return None, None


def _issue(code: str, message: str, path: Path) -> JourneyIssue:
    """Create a blocking run issue."""
    return JourneyIssue(code=code, severity=JourneySeverity.ERROR, message=message, path=path)


__all__ = ["JourneyRunResult", "run_journeys"]
