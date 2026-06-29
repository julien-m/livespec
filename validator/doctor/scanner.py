# LiveSpec traceability anchors
# @spec(FR-003)
# @spec(FR-004)
# @spec(FR-005)
# @spec(FR-006)
# @spec(FR-007)
# @spec(FR-008)
# @spec(FR-010)
# @spec(FR-013)

"""Project health scanner for ``livespec doctor``."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import frontmatter

from validator.coherence.rule_engine import run_coherence
from validator.coherence.violation import Severity
from validator.conventions_receipt_policy import evaluate_conventions_receipt_policy
from validator.journeys import scan_journeys
from validator.journeys.models import JourneySeverity

from .models import CleanupAction, DoctorFinding, DoctorReport, DoctorSeverity, DoctorStatus

# Markdown table rows with pipe-delimited cells.
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
# Backticked file paths inside implementation map cells.
_BACKTICK_PATH_RE = re.compile(r"`([^`]+)`")
# Requirement identifiers accepted by implementation maps.
_REQ_RE = re.compile(r"^(?:FR|AC)-\d+$")

_PATH_SUFFIXES = {
    ".css",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".kt",
    ".lock",
    ".md",
    ".pdf",
    ".pen",
    ".png",
    ".py",
    ".rs",
    ".sh",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


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
    findings.extend(_scan_conventions_receipt_policy(project_root))
    findings.extend(_scan_lifecycle(specs_root))
    findings.extend(_scan_journey_health(project_root))
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


def _scan_journey_health(project_root: Path) -> list[DoctorFinding]:
    """Add executable user journey findings to the doctor report."""
    # @spec FR-013: Journey scan handoff
    # — .specs/features/056-executable-user-journeys/spec.md#fr-013
    report = scan_journeys(project_root)
    return [
        DoctorFinding(
            code=finding.code,
            severity=_from_journey_severity(finding.severity),
            category="journeys",
            message=finding.message,
            feature=finding.feature,
            requirement=finding.requirement,
            path=finding.path.as_posix(),
            suggested_action="Run `livespec journey validate` or `livespec journey compile`.",
        )
        for finding in report.findings
    ]


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
                is_test_mapping = "test" in section or _is_test_reference(raw_path)
                if is_test_mapping:
                    mapped_tests.append(resolved)
                if _mapped_path_exists(project_root, raw_path):
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
        if _runner_mentions_test(relative_path, test_path.name, runner_text):
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


def _runner_mentions_test(relative_path: str, test_name: str, runner_text: str) -> bool:
    """Return whether runner metadata includes a test path, file, or parent dir."""
    if relative_path in runner_text or test_name in runner_text:
        return True
    parts = relative_path.split("/")
    parent_dirs = ("/".join(parts[:idx]) for idx in range(1, len(parts)))
    return any(parent_dir and parent_dir in runner_text for parent_dir in parent_dirs)


def _scan_hook_enforcement(project_root: Path) -> list[DoctorFinding]:
    """Report missing commit/push hook enforcement."""
    # @spec FR-007: Hooks — .specs/features/055-spec-doctor-project-health/spec.md#fr-007
    hook_paths = [
        project_root / ".git" / "hooks" / "pre-commit",
        project_root / ".git" / "hooks" / "pre-push",
        project_root / ".githooks" / "pre-commit",
        project_root / ".githooks" / "pre-push",
    ]
    hook_paths.extend(_git_resolved_hook_paths(project_root))
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


def _git_resolved_hook_paths(project_root: Path) -> list[Path]:
    """Return hook paths as Git resolves them, including linked worktrees."""
    resolved: list[Path] = []
    for hook_name in ("pre-commit", "pre-push"):
        try:
            proc = subprocess.run(
                [
                    "git",
                    "-C",
                    project_root.as_posix(),
                    "rev-parse",
                    "--git-path",
                    f"hooks/{hook_name}",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode != 0:
            continue
        raw_path = proc.stdout.strip()
        if not raw_path:
            continue
        resolved.append(Path(raw_path))
    return resolved


def _scan_conventions_receipt_policy(project_root: Path) -> list[DoctorFinding]:
    """Surface AST conventions rollout findings in doctor."""
    policy = evaluate_conventions_receipt_policy(project_root, command="doctor")
    if policy.state in {"unchanged", "pass"}:
        return []
    if policy.state == "observe_warning":
        return [
            DoctorFinding(
                code="conventions_ast_observe",
                severity=DoctorSeverity.WARNING,
                category="conventions",
                message=policy.reason,
                suggested_action=(
                    "Review AST observations before switching ast_rules.mode to enforce."
                ),
            )
        ]
    return [
        DoctorFinding(
            code="conventions_ast_enforce",
            severity=DoctorSeverity.ERROR,
            category="conventions",
            message=policy.reason,
            suggested_action="Run `livespec conventions verify --feature repo --json`.",
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
        project_root / "playwright.config.ts",
        project_root / "playwright.config.js",
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
        backticked_values = _BACKTICK_PATH_RE.findall(cell)
        raw_values = backticked_values or [cell]
        for raw_value in raw_values:
            for value in re.split(r",|\n", raw_value):
                cleaned = value.strip().strip("`")
                if _looks_like_path(cleaned, explicit=bool(backticked_values)):
                    paths.append(cleaned)
    return paths


def _looks_like_path(value: str, *, explicit: bool) -> bool:
    """Return True when a table value resembles a file path."""
    if (
        not value
        or value.startswith(("@spec", "#", "/spec.", "/spec-"))
        or value in {".reserved", ".specs/.LOCK"}
    ):
        return False
    if any(token in value for token in ("(", ")", "{", "}", "[feature]")):
        return False
    if any(char.isspace() for char in value):
        return False
    path_part = value.split("::", 1)[0]
    if "/" in path_part or path_part.startswith("."):
        return True
    if explicit:
        return Path(path_part).suffix.lower() in _PATH_SUFFIXES
    return False


def _resolve_project_path(project_root: Path, raw_path: str) -> Path:
    """Resolve a mapping path relative to the project root."""
    path = Path(_path_part(raw_path))
    if path.is_absolute():
        return path
    return project_root / path


def _mapped_path_exists(project_root: Path, raw_path: str) -> bool:
    """Return True when a mapped file path, test selector, or glob resolves."""
    path_part = _path_part(raw_path)
    path = Path(path_part)
    if any(char in path_part for char in "*?[]"):
        if path.is_absolute():
            return any(path.parent.glob(path.name))
        return any(project_root.glob(path_part))
    return _resolve_project_path(project_root, raw_path).exists()


def _path_part(raw_path: str) -> str:
    """Strip test selectors and Markdown line suffixes from a mapped path."""
    path_part = raw_path.split("::", 1)[0]
    match = re.match(r"^(.+\.[A-Za-z0-9]+):\d+$", path_part)
    if match:
        return match.group(1)
    return path_part


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


def _is_test_reference(raw_path: str) -> bool:
    """Return True when a mapped path points to an executable test artifact."""
    path_part = _path_part(raw_path)
    path = Path(path_part)
    lower = path_part.lower()
    return (
        lower.startswith("tests/")
        or "/tests/" in lower
        or "uitests/" in lower
        or path.name.startswith("test_")
        or path.name.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
    )


def _from_coherence_severity(severity: Severity) -> DoctorSeverity:
    """Map coherence severities to doctor severities."""
    if severity == Severity.ERROR:
        return DoctorSeverity.ERROR
    if severity == Severity.WARNING:
        return DoctorSeverity.WARNING
    return DoctorSeverity.INFO


def _from_journey_severity(severity: JourneySeverity) -> DoctorSeverity:
    """Map journey severities to doctor severities."""
    if severity == JourneySeverity.ERROR:
        return DoctorSeverity.ERROR
    if severity == JourneySeverity.WARNING:
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
