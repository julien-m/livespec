"""Project health scanner for ``livespec doctor``."""

from __future__ import annotations

import re
from pathlib import Path

import frontmatter

from validator.coherence.rule_engine import run_coherence
from validator.coherence.violation import Severity

from .models import CleanupAction, DoctorFinding, DoctorReport, DoctorSeverity, DoctorStatus

# Markdown table rows with pipe-delimited cells.
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
# Backticked file paths inside implementation map cells.
_BACKTICK_PATH_RE = re.compile(r"`([^`]+)`")
# Requirement identifiers accepted by implementation maps.
_REQ_RE = re.compile(r"^(?:FR|AC)-\d+$")


def run_doctor(
    project_root: Path,
    *,
    strict: bool = False,
    fix_plan: bool = False,
    apply_cleanup: bool = False,
) -> DoctorReport:
    """Run the full project doctor audit.

    Args:
        project_root: Root containing ``.specs/``.
        strict: Promote warnings to errors.
        fix_plan: Include non-destructive cleanup proposals.
        apply_cleanup: Refuse destructive cleanup actions while reporting them.

    Returns:
        A complete doctor report.
    """
    # @spec FR-003: Package — .specs/features/055-spec-doctor-project-health/spec.md#fr-003
    # @spec FR-010: Journey checks optional — spec.md#fr-010
    specs_root = project_root / ".specs"
    findings: list[DoctorFinding] = []
    cleanup_actions: list[CleanupAction] = []

    findings.extend(_scan_coherence(specs_root))
    mapped_tests = _scan_implementation_maps(project_root, specs_root, findings)
    findings.extend(_scan_runner_inclusion(project_root, specs_root, mapped_tests))
    findings.extend(_scan_hook_enforcement(project_root))
    findings.extend(_scan_lifecycle(specs_root))
    visual_findings, visual_actions = _scan_visual_orphans(specs_root)
    findings.extend(visual_findings)
    if fix_plan or apply_cleanup:
        cleanup_actions.extend(visual_actions)
    if apply_cleanup:
        cleanup_actions = [
            CleanupAction(
                code=action.code,
                path=action.path,
                description=action.description,
                destructive=action.destructive,
                refused=action.destructive,
            )
            for action in cleanup_actions
        ]

    status = _resolve_status(findings, strict=strict)
    return DoctorReport(
        status=status,
        findings=findings,
        cleanup_actions=cleanup_actions,
        strict=strict,
    )


def _scan_coherence(specs_root: Path) -> list[DoctorFinding]:
    """Include existing Layer 2 coherence validation in the doctor report."""
    # @spec FR-004: Coherence — .specs/features/055-spec-doctor-project-health/spec.md#fr-004
    if not specs_root.exists():
        return [
            DoctorFinding(
                code="specs_missing",
                severity=DoctorSeverity.ERROR,
                category="coherence",
                message=".specs directory is missing.",
                path=str(specs_root),
                suggested_action="Run /spec-init before doctor.",
            )
        ]
    result = run_coherence(specs_root)
    findings: list[DoctorFinding] = []
    for violation in result.violations:
        findings.append(
            DoctorFinding(
                code=violation.rule_id,
                severity=_from_coherence_severity(violation.severity),
                category="coherence",
                message=violation.message,
                feature=_context_feature(violation.context),
                suggested_action=violation.fix_hint,
            )
        )
    return findings


def _scan_implementation_maps(
    project_root: Path,
    specs_root: Path,
    findings: list[DoctorFinding],
) -> list[Path]:
    """Scan implementation maps for stale code and test references."""
    # @spec FR-005: Maps — .specs/features/055-spec-doctor-project-health/spec.md#fr-005
    # Strategy: walk Markdown mapping tables, extract backticked paths, then classify AC
    # rows and test sections as executable test mappings for downstream runner checks.
    mapped_tests: list[Path] = []
    for implementation_path in sorted((specs_root / "features").glob("*/implementation.md")):
        feature = implementation_path.parent.name
        section = ""
        for line in implementation_path.read_text().splitlines():
            if line.startswith("## "):
                section = line.lower()
            if not _TABLE_ROW_RE.match(line.strip()) or "---" in line:
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not cells or not _REQ_RE.match(cells[0]):
                continue
            requirement = cells[0]
            for raw_path in _extract_paths_from_cells(cells[1:]):
                resolved = _resolve_project_path(project_root, raw_path)
                is_test_mapping = requirement.startswith("AC-") or "test" in section
                if is_test_mapping:
                    mapped_tests.append(resolved)
                if resolved.exists():
                    continue
                findings.append(
                    DoctorFinding(
                        code="missing_test_file" if is_test_mapping else "mapping_stale",
                        severity=DoctorSeverity.ERROR,
                        category="implementation_maps",
                        message=f"{requirement} maps to missing file {raw_path}.",
                        feature=feature,
                        requirement=requirement,
                        path=raw_path,
                        suggested_action="Update implementation.md or restore the referenced file.",
                    )
                )
    return mapped_tests


def _scan_runner_inclusion(
    project_root: Path,
    specs_root: Path,
    mapped_tests: list[Path],
) -> list[DoctorFinding]:
    """Verify mapped tests are included by configured runner metadata."""
    # @spec FR-006: Runners — .specs/features/055-spec-doctor-project-health/spec.md#fr-006
    existing_tests = [path for path in mapped_tests if path.exists()]
    if not existing_tests:
        return []
    runner_text = _runner_config_text(project_root, specs_root)
    findings: list[DoctorFinding] = []
    for test_path in existing_tests:
        if test_path.is_relative_to(project_root):
            relative_path = test_path.relative_to(project_root).as_posix()
        else:
            relative_path = test_path.as_posix()
        if relative_path in runner_text or test_path.name in runner_text:
            continue
        if _is_default_pytest_discovered(test_path, project_root):
            continue
        findings.append(
            DoctorFinding(
                code="test_not_in_runner",
                severity=DoctorSeverity.WARNING,
                category="runners",
                message=f"Mapped test {relative_path} is not included by runner configuration.",
                path=relative_path,
                suggested_action=(
                    "Add the test to .specs/surfaces.yaml or the active test driver config."
                ),
            )
        )
    return findings


def _scan_hook_enforcement(project_root: Path) -> list[DoctorFinding]:
    """Report missing commit/push hook enforcement."""
    # @spec FR-007: Hooks — .specs/features/055-spec-doctor-project-health/spec.md#fr-007
    hook_paths = [
        project_root / ".git" / "hooks" / "pre-commit",
        project_root / ".git" / "hooks" / "pre-push",
        project_root / ".githooks" / "pre-commit",
        project_root / ".githooks" / "pre-push",
    ]
    for hook_path in hook_paths:
        if not hook_path.exists():
            continue
        content = hook_path.read_text(errors="ignore")
        if "livespec" in content and ("validate" in content or "doctor" in content):
            return []
    return [
        DoctorFinding(
            code="hook_unenforced",
            severity=DoctorSeverity.WARNING,
            category="hooks",
            message="No git hook appears to enforce LiveSpec validation.",
            suggested_action="Install or update hooks so commit/push runs livespec validate.",
        )
    ]


def _scan_lifecycle(specs_root: Path) -> list[DoctorFinding]:
    """Detect deprecated specs without explicit supersession metadata."""
    # @spec AC-007: Linked — .specs/features/055-spec-doctor-project-health/spec.md#ac-007
    # @spec AC-008: Missing — .specs/features/055-spec-doctor-project-health/spec.md#ac-008
    findings: list[DoctorFinding] = []
    for spec_path in sorted((specs_root / "features").glob("*/spec.md")):
        post = frontmatter.load(str(spec_path))
        status = str(post.metadata.get("status", "")).lower()
        has_successor = bool(
            post.metadata.get("superseded_by") or post.metadata.get("deprecated_reason")
        )
        if status in {"deprecated", "obsolete", "superseded"} and not has_successor:
            findings.append(
                DoctorFinding(
                    code="supersession_missing",
                    severity=DoctorSeverity.WARNING,
                    category="lifecycle",
                    message=f"{spec_path.parent.name} is {status} without supersession metadata.",
                    feature=spec_path.parent.name,
                    path=str(spec_path.relative_to(specs_root.parent)),
                    suggested_action="Add superseded_by or deprecated_reason metadata.",
                )
            )
    return findings


def _scan_visual_orphans(specs_root: Path) -> tuple[list[DoctorFinding], list[CleanupAction]]:
    """Find visual evidence directories not tied to active features."""
    # @spec FR-008: Visual — .specs/features/055-spec-doctor-project-health/spec.md#fr-008
    # Strategy: compare evidence directory names against active feature directories and
    # emit both a finding and a refused cleanup plan so the audit remains non-destructive.
    feature_dirs = {path.name for path in (specs_root / "features").glob("*") if path.is_dir()}
    findings: list[DoctorFinding] = []
    actions: list[CleanupAction] = []
    for visual_root in [specs_root / "design" / "baselines", specs_root / "design" / "receipts"]:
        if not visual_root.exists():
            continue
        for child in sorted(visual_root.iterdir()):
            if not child.is_dir() or child.name in feature_dirs:
                continue
            relative_path = child.relative_to(specs_root.parent).as_posix()
            findings.append(
                DoctorFinding(
                    code="visual_orphan",
                    severity=DoctorSeverity.ERROR,
                    category="visual",
                    message=(
                        f"Visual evidence directory {relative_path} has no active feature mapping."
                    ),
                    feature=child.name,
                    path=relative_path,
                    suggested_action=(
                        "Review the evidence and archive it intentionally if obsolete."
                    ),
                    autofixable=False,
                )
            )
            actions.append(
                CleanupAction(
                    code="visual_orphan",
                    path=relative_path,
                    description="Archive or remove orphaned visual evidence after human review.",
                    destructive=True,
                )
            )
    return findings, actions


def _runner_config_text(project_root: Path, specs_root: Path) -> str:
    """Return runner configuration text used for inclusion checks."""
    candidates = [
        specs_root / "surfaces.yaml",
        specs_root / "surfaces.yml",
        specs_root / "testing" / "strategy.md",
        project_root / "pytest.ini",
        project_root / "pyproject.toml",
    ]
    parts: list[str] = []
    for path in candidates:
        if not path.exists():
            continue
        content = path.read_text(errors="ignore")
        parts.append(content)
    return "\n".join(parts)


def _extract_paths_from_cells(cells: list[str]) -> list[str]:
    """Extract path-like values from Markdown table cells."""
    paths: list[str] = []
    for cell in cells:
        raw_values = _BACKTICK_PATH_RE.findall(cell) or [cell]
        for raw_value in raw_values:
            for value in re.split(r",|\n", raw_value):
                cleaned = value.strip().strip("`")
                if _looks_like_path(cleaned):
                    paths.append(cleaned)
    return paths


def _looks_like_path(value: str) -> bool:
    """Return True when a table value resembles a file path."""
    if not value or value.startswith("@spec"):
        return False
    return "/" in value or "." in Path(value).name


def _resolve_project_path(project_root: Path, raw_path: str) -> Path:
    """Resolve a mapping path relative to the project root."""
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return project_root / path


def _is_default_pytest_discovered(test_path: Path, project_root: Path) -> bool:
    """Return True for tests picked up by pytest's default discovery."""
    if not test_path.is_relative_to(project_root):
        return False
    relative = test_path.relative_to(project_root)
    return (
        len(relative.parts) >= 2
        and relative.parts[0] == "tests"
        and relative.name.startswith("test_")
        and relative.suffix == ".py"
    )


def _from_coherence_severity(severity: Severity) -> DoctorSeverity:
    """Map coherence severities to doctor severities."""
    if severity == Severity.ERROR:
        return DoctorSeverity.ERROR
    if severity == Severity.WARNING:
        return DoctorSeverity.WARNING
    return DoctorSeverity.INFO


def _context_feature(context: dict[str, object]) -> str | None:
    """Extract a feature slug from a coherence violation context."""
    value = context.get("feature_dir") or context.get("feature")
    return value if isinstance(value, str) else None


def _resolve_status(findings: list[DoctorFinding], *, strict: bool) -> DoctorStatus:
    """Resolve the top-level status from findings and strict mode."""
    if any(finding.severity == DoctorSeverity.ERROR for finding in findings):
        return DoctorStatus.FAIL
    has_warning = any(finding.severity == DoctorSeverity.WARNING for finding in findings)
    if has_warning and strict:
        return DoctorStatus.FAIL
    if has_warning:
        return DoctorStatus.WARN
    return DoctorStatus.OK


__all__ = ["run_doctor"]
