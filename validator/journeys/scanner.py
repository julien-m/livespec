"""Spec Doctor integration and category reporting for journeys."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .backlinks import verify_feature_backlinks
from .manifest import read_compiled_manifest
from .models import JourneyFinding, JourneyReport, JourneySeverity
from .paths import iter_journey_source_paths, iter_v1_journey_source_paths
from .validator import validate_journeys

_AC_RE = re.compile(r"\*\*(AC-\d+):")
_FR_RE = re.compile(r"\*\*(FR-\d+):")


def scan_journeys(project_root: Path, feature: str | None = None) -> JourneyReport:
    """Scan journeys for doctor findings and category counts.

    Args:
        project_root: Project root containing `.specs/`.
        feature: Optional feature slug.

    Returns:
        Journey report with findings and category counts.
    """
    validation = validate_journeys(project_root, feature)
    findings = [
        JourneyFinding(
            code=issue.code,
            severity=issue.severity,
            message=issue.message,
            path=issue.path,
        )
        for issue in validation.issues
    ]
    findings.extend(
        JourneyFinding(
            code=issue.code,
            severity=issue.severity,
            message=issue.message,
            path=issue.path,
        )
        for issue in verify_feature_backlinks(project_root)
    )
    findings.extend(
        JourneyFinding(
            code="journey_v1_leftover",
            severity=JourneySeverity.WARNING,
            message="Legacy v1 journey source remains; run livespec journey migrate --from-v1.",
            path=path,
        )
        for path in iter_v1_journey_source_paths(project_root)
    )
    findings.extend(_scan_manifest_stale_for_all_sources(project_root, findings))
    for journey in validation.journeys:
        findings.extend(_scan_requirement_drift(project_root, journey))
        if journey.disabled:
            findings.append(
                JourneyFinding(
                    code="journey_disabled",
                    severity=JourneySeverity.INFO,
                    message=f"Journey {journey.journey_id} is disabled and will not execute.",
                    path=journey.path,
                    feature=journey.feature,
                )
            )
        if journey.is_manual:
            findings.append(
                JourneyFinding(
                    code="journey_manual",
                    severity=JourneySeverity.INFO,
                    message=f"Journey {journey.journey_id} is manual: {journey.manual_reason}.",
                    path=journey.path,
                    feature=journey.feature,
                )
            )
        if journey.is_executable:
            findings.extend(_scan_compiled_artifact(project_root, journey))
    return JourneyReport(journeys=validation.journeys, findings=findings)


def _scan_manifest_stale_for_all_sources(
    project_root: Path,
    existing: list[JourneyFinding],
) -> list[JourneyFinding]:
    """Report stale manifests even when cross-file validation rejects the source."""
    existing_stale_paths = {
        finding.path for finding in existing if finding.code == "journey_compiled_stale"
    }
    findings: list[JourneyFinding] = []
    for path in iter_journey_source_paths(project_root):
        journey_id = path.parent.name
        manifest = read_compiled_manifest(project_root, journey_id)
        if manifest is None or path in existing_stale_paths:
            continue
        source_hash = hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        if manifest.source_hash != source_hash:
            findings.append(
                JourneyFinding(
                    code="journey_compiled_stale",
                    severity=JourneySeverity.ERROR,
                    message=f"Compiled manifest for journey {journey_id} has a stale source hash.",
                    path=path,
                )
            )
    return findings


def _scan_requirement_drift(project_root: Path, journey: object) -> list[JourneyFinding]:
    """Report journey coverage references that no longer exist in spec.md."""
    from .models import JourneyFile

    typed = journey if isinstance(journey, JourneyFile) else None
    if typed is None:
        return []
    spec_path = project_root / ".specs" / "features" / typed.feature / "spec.md"
    if not spec_path.exists():
        return [
            JourneyFinding(
                code="journey_feature_missing",
                severity=JourneySeverity.ERROR,
                message=f"Feature {typed.feature} referenced by journey is missing.",
                path=typed.path,
                feature=typed.feature,
            )
        ]
    spec_text = spec_path.read_text(encoding="utf-8", errors="ignore")
    known_ac = set(_AC_RE.findall(spec_text))
    known_fr = set(_FR_RE.findall(spec_text))
    findings: list[JourneyFinding] = []
    for requirement in typed.covers_ac:
        if requirement not in known_ac:
            findings.append(_missing_requirement(typed.path, typed.feature, requirement))
    for requirement in typed.covers_fr:
        if requirement not in known_fr:
            findings.append(_missing_requirement(typed.path, typed.feature, requirement))
    return findings


def _scan_compiled_artifact(project_root: Path, journey: object) -> list[JourneyFinding]:
    """Report missing or stale compiled artifacts for executable journeys."""
    from .models import JourneyFile

    typed = journey if isinstance(journey, JourneyFile) else None
    if typed is None:
        return []
    manifest = read_compiled_manifest(project_root, typed.journey_id)
    if manifest is None:
        return [
            JourneyFinding(
                code="journey_compiled_missing",
                severity=JourneySeverity.WARNING,
                message=f"Compiled artifact is missing for journey {typed.journey_id}.",
                path=typed.path,
                feature=typed.feature,
            )
        ]
    if manifest.source_hash != typed.source_hash:
        return [
            JourneyFinding(
                code="journey_compiled_stale",
                severity=JourneySeverity.ERROR,
                message=(
                    f"Compiled artifact for journey {typed.journey_id} has a stale source hash."
                ),
                path=typed.path,
                feature=typed.feature,
            )
        ]
    return []


def _missing_requirement(path: Path, feature: str, requirement: str) -> JourneyFinding:
    """Create a missing requirement finding."""
    return JourneyFinding(
        code="journey_requirement_missing",
        severity=JourneySeverity.ERROR,
        message=f"Journey covers missing or removed requirement {requirement}.",
        path=path,
        feature=feature,
        requirement=requirement,
    )
