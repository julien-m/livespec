"""Scoped bugfix gate: owner, requirement text, RED/GREEN and confinement (feature 084)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..identity import SLUG_REGEX
from .config import CONFIG_PATH, parse_limits
from .diff import DiffEntry, DiffUnavailableError, base_text, collect_diff, is_traceability_artifact
from .models import BugfixLimits, FallbackReason, GateReport
from .receipts import ObservedRun, is_test_file, observe, regression_reasons
from .requirements import changed_requirements, requirement_scope_reasons


@dataclass(frozen=True)
class GateRequest:
    """Inputs of one evaluation; `green` absent means the pre-edit gate."""

    project_root: Path
    feature: str
    red: Path
    green: Path | None = None
    requirements: tuple[str, ...] = field(default_factory=tuple)
    base: str = "HEAD"


# @spec FR-003: Owner feature identification
#   — .specs/features/084-bugfix-lane/spec.md#fr-003
def owner_reasons(project_root: Path, feature: str) -> list[FallbackReason]:
    """Require the feature directory with both spec.md and implementation.md."""
    if not SLUG_REGEX.fullmatch(feature):
        return [FallbackReason("owner_not_identified", f"invalid feature slug {feature!r}")]
    feature_dir = project_root / ".specs" / "features" / feature
    for path in (feature_dir, feature_dir / "spec.md", feature_dir / "implementation.md"):
        if not path.exists():
            return [FallbackReason("owner_not_identified", f"missing {path}")]
    return []


# @spec FR-007: Scoped gate without whole-feature readiness
#   — .specs/features/084-bugfix-lane/spec.md#fr-007
def evaluate_gate(request: GateRequest) -> GateReport:
    """Collect every failed condition (plan D-07); never call the complete readiness gate.

    Raises:
        BugfixConfigError: `.specs/bugfix.yaml` is invalid (the CLI exits 3).
    """
    root = request.project_root
    reasons: list[FallbackReason] = []
    diff = _diff(root, request.base, reasons)
    # Limits come from the base revision; without a diff the gate falls back anyway.
    config = base_text(root, request.base, CONFIG_PATH) if diff is not None else None
    limits = parse_limits(config, f"{request.base}:{CONFIG_PATH}")
    report = GateReport(request.feature, request.green is not None, limits)
    owner = owner_reasons(root, request.feature)
    report.reasons += owner + reasons
    if diff is not None:
        report.reasons += _spec_text_reasons(root, request.base, diff)
    if not owner:
        report.reasons += requirement_scope_reasons(root, request.feature, request.requirements)
    red = _observed(root, request, request.red, "red", report)
    if request.green is None:
        return report
    green = _observed(root, request, request.green, "green", report)
    if red is not None and green is not None:
        paths = None if diff is None else {entry.path for entry in diff}
        report.regression_tests, reasons = regression_reasons(red, green, paths)
        report.reasons += reasons
    if diff is not None:
        report.reasons += _existing_test_reasons(root, request.base, diff, report)
        report.reasons += _confinement_reasons(diff, report)
    return report


def _existing_test_reasons(
    root: Path, base: str, diff: list[DiffEntry], report: GateReport
) -> list[FallbackReason]:
    """Reject edits of tests that existed at the base, except the Regression test files."""
    regression_files = {node.split("::", 1)[0] for node in report.regression_tests}
    return [
        FallbackReason("existing_test_changed", entry.path)
        for entry in diff
        if is_test_file(entry.path)
        and entry.path not in regression_files
        and not is_traceability_artifact(entry.path)
        and base_text(root, base, entry.path) is not None
    ]


def _diff(root: Path, base: str, reasons: list[FallbackReason]) -> list[DiffEntry] | None:
    try:
        return collect_diff(root, base)
    except DiffUnavailableError as exc:
        reasons.append(FallbackReason("diff_unavailable", str(exc)))
        return None


# @spec FR-004: Requirement text unchanged
#   — .specs/features/084-bugfix-lane/spec.md#fr-004
def _spec_text_reasons(root: Path, base: str, diff: list[DiffEntry]) -> list[FallbackReason]:
    reasons: list[FallbackReason] = []
    for entry in diff:
        if not entry.path.startswith(".specs/") or not entry.path.endswith("/spec.md"):
            continue
        current = root / entry.path
        after = current.read_text(encoding="utf-8") if current.is_file() else None
        changed = changed_requirements(base_text(root, base, entry.path), after)
        if changed:
            detail = f"{entry.path}: {', '.join(changed)}"
            reasons.append(FallbackReason("spec_requirement_text_changed", detail))
    return reasons


def _observed(
    root: Path, request: GateRequest, receipt: Path, expected: str, report: GateReport
) -> ObservedRun | None:
    run, gaps = observe(root, request.feature, receipt, expected)
    if gaps:
        report.reasons.append(FallbackReason(f"{expected}_receipt_invalid", "; ".join(gaps)))
        return None
    if run is not None:
        invocation = run.capture.invocation
        if expected == "red":
            report.red_invocation = invocation
        else:
            report.green_invocation = invocation
    return run


# @spec FR-006: Diff confinement
#   — .specs/features/084-bugfix-lane/spec.md#fr-006
def _confinement_reasons(diff: list[DiffEntry], report: GateReport) -> list[FallbackReason]:
    counted = [entry for entry in diff if not is_traceability_artifact(entry.path)]
    report.counted_files = [entry.path for entry in counted]
    report.counted_lines = sum(entry.lines for entry in counted)
    limits: BugfixLimits = report.limits
    reasons = [FallbackReason("diff_binary", entry.path) for entry in counted if entry.binary]
    if len(counted) > limits.max_files or report.counted_lines > limits.max_lines:
        reasons.append(
            FallbackReason(
                "diff_too_large",
                f"files {len(counted)}/{limits.max_files}, "
                f"lines {report.counted_lines}/{limits.max_lines}",
            )
        )
    return reasons
