# LiveSpec traceability anchors
# @spec(FR-008)
# @spec(FR-019)
# @spec(FR-020)
# @spec(FR-021)
# @spec(FR-032)

"""Impact analysis for global User Journeys v2."""

# @spec FR-008, FR-019, FR-020, FR-021: impact records and pre-failure journey impact detection
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-019

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]  # PyYAML has no typed metadata.
from pydantic import ValidationError

from validator.selector import SmartTestSelector

from .paths import iter_journey_source_paths
from .schema import JourneySourceV2, JourneyTargetRef


@dataclass(frozen=True)
class JourneyImpact:
    """One detected impact between a changed file and a journey."""

    journey_id: str
    reason: str
    source_signal: str
    confidence: int
    affected_features: list[str]
    required_classification: str
    recommended_command: str
    blocking: bool


def analyze_journey_impacts(
    project_root: Path,
    *,
    changed_files: list[Path],
) -> list[JourneyImpact]:
    """Analyze changed files against v2 journey targets and visual contracts."""
    changed_text = "\n".join(_read_changed_file(path) for path in changed_files)
    selector_features = _selector_features(project_root, changed_files)
    impacts: dict[tuple[str, str], JourneyImpact] = {}
    for source_path in iter_journey_source_paths(project_root):
        source = _read_source(source_path)
        if source is None:
            continue
        affected_features = sorted({cover.feature for cover in source.covers})
        if selector_features.intersection(affected_features):
            key = (source.id, "smart_test_selector")
            impacts[key] = JourneyImpact(
                journey_id=source.id,
                reason=(
                    "SmartTestSelector matched changed files to covered features "
                    f"{sorted(selector_features.intersection(affected_features))}"
                ),
                source_signal="smart_test_selector",
                confidence=80,
                affected_features=affected_features,
                required_classification="intentional_update",
                recommended_command=f"$spec-journey edit {source.id}",
                blocking=True,
            )
        for signal_name, value in _target_signals(source):
            if value and value in changed_text:
                key = (source.id, signal_name)
                impacts[key] = JourneyImpact(
                    journey_id=source.id,
                    reason=f"changed files mention journey {signal_name} target {value!r}",
                    source_signal=signal_name,
                    confidence=90,
                    affected_features=affected_features,
                    required_classification="intentional_update",
                    recommended_command=f"$spec-journey edit {source.id}",
                    blocking=True,
                )
    return sorted(impacts.values(), key=lambda impact: (impact.journey_id, impact.source_signal))


def _selector_features(project_root: Path, changed_files: list[Path]) -> set[str]:
    """Use SmartTestSelector when `.specs/` exists, otherwise return no selector signal."""
    specs_root = project_root / ".specs"
    if not specs_root.exists():
        return set()
    return SmartTestSelector(specs_root).from_changed_files(changed_files)


def _read_source(path: Path) -> JourneySourceV2 | None:
    """Read a v2 journey source, returning None when invalid."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return JourneySourceV2.model_validate(data)
    except (OSError, yaml.YAMLError, ValidationError):
        return None


def _read_changed_file(path: Path) -> str:
    """Read changed file text for deterministic local impact checks."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _target_signals(source: JourneySourceV2) -> list[tuple[str, str]]:
    """Return stable target signals used by journey actions and visual checks."""
    signals: list[tuple[str, str]] = []
    for step in source.steps:
        if step.target is not None:
            signals.extend(_target_ref_signals(step.target, prefix="target"))
    for check in source.visual_checks:
        signals.extend(_target_ref_signals(check.target, prefix="visual_check"))
    return signals


def _target_ref_signals(target: JourneyTargetRef, *, prefix: str) -> list[tuple[str, str]]:
    """Extract every stable selector field that can connect a diff to a journey."""
    signals: list[tuple[str, str]] = []
    for field_name in (
        "semantic_id",
        "test_id",
        "i18n_key",
        "accessibility_label",
        "route",
        "label",
    ):
        value = getattr(target, field_name)
        if value:
            signals.append((f"{prefix}_{field_name}", value))
    if target.role:
        signals.append((f"{prefix}_role", target.role))
    if target.name:
        signals.append((f"{prefix}_name", target.name))
    if target.text and target.product_contract:
        signals.append((f"{prefix}_text", target.text))
    return signals


__all__ = ["JourneyImpact", "analyze_journey_impacts"]
