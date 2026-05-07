"""Local patch coverage computation — intersect lcov.info with git diff."""

# @spec FR-005: Patch coverage is computed locally from lcov and unified diff data.
# @spec AC-012: No hosted service participates in changed-line coverage calculation.
# @spec AC-015: The implementation stays local and avoids external coverage vendors.


from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .schemas import PatchCoverageReport

# Match lcov execution counts like ``DA:<line>,<hits>`` for one source file.
_DA_RE = re.compile(r"^DA:(\d+),(\d+)")
# Match lcov source-file markers like ``SF:path/to/file``.
_SF_RE = re.compile(r"^SF:(.+)")
# Match unified-diff target file headers like ``+++ b/path/to/file``.
_DIFF_FILE_RE = re.compile(r"^\+\+\+ b/(.+)$")
# Match unified-diff hunk headers and capture the new-file line start/count.
_DIFF_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def parse_lcov(path: Path) -> dict[str, dict[int, bool]]:
    """Parse an ``lcov.info`` file into line coverage data.

    Args:
        path: Coverage report path to parse.

    Returns:
        Mapping of source file path to line-number coverage booleans.
    """
    coverage_by_file: dict[str, dict[int, bool]] = {}
    if not path.exists():
        return coverage_by_file
    current_file: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("SF:"):
            match = _SF_RE.match(line)
            if match:
                source_file = match.group(1)
                current_file = source_file
                coverage_by_file.setdefault(source_file, {})
        elif line == "end_of_record":
            current_file = None
        elif current_file is not None and line.startswith("DA:"):
            match = _DA_RE.match(line)
            if match:
                line_number = int(match.group(1))
                hit_count = int(match.group(2))
                coverage_by_file[current_file][line_number] = hit_count > 0
    return coverage_by_file


def parse_diff(diff_text: str) -> dict[str, set[int]]:
    """Parse a unified diff into changed target lines.

    Args:
        diff_text: Unified diff text, typically from ``git diff --unified=0``.

    Returns:
        Mapping of file path to added or modified line numbers in the new file.
    """
    changed_lines_by_file: dict[str, set[int]] = {}
    current_file: str | None = None
    new_line_no = 0
    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            match = _DIFF_FILE_RE.match(raw)
            if match:
                file_path = match.group(1)
                if file_path == "/dev/null":
                    current_file = None
                else:
                    current_file = file_path
                    changed_lines_by_file.setdefault(file_path, set())
            continue
        if raw.startswith("@@"):
            match = _DIFF_HUNK_RE.match(raw)
            if match and current_file is not None:
                new_line_no = int(match.group(1))
            continue
        if current_file is None:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            changed_lines_by_file[current_file].add(new_line_no)
            new_line_no += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            continue
        else:
            new_line_no += 1
    return changed_lines_by_file


def _normalise_lcov_path(p: str) -> str:
    """Normalize source paths so lcov and git diff file keys can be compared."""
    return p.replace("\\", "/").removeprefix("./")


def compute_patch_coverage(
    lcov_path: Path,
    diff_text: str,
    *,
    project_root: Path | None = None,
) -> PatchCoverageReport:
    """Compute changed-line coverage from lcov data and a diff.

    Args:
        lcov_path: Coverage report path to parse.
        diff_text: Unified diff text whose changed lines should be measured.
        project_root: Optional repository root used to normalize absolute paths.

    Returns:
        Aggregate and per-file patch coverage information.
    """
    lcov_data = parse_lcov(lcov_path)
    diff_data = parse_diff(diff_text)

    # Keep both project-relative and raw lcov paths so reports work whether the
    # coverage tool emits absolute filenames or already-normalized repository paths.
    normalized_lcov: dict[str, dict[int, bool]] = {}
    root = project_root or Path.cwd()
    for source_file, line_coverage in lcov_data.items():
        relative_path = source_file
        try:
            relative_path = str(Path(source_file).resolve().relative_to(root.resolve()))
        except (ValueError, OSError):
            relative_path = _normalise_lcov_path(source_file)
        normalized_lcov[_normalise_lcov_path(relative_path)] = line_coverage
        normalized_lcov[_normalise_lcov_path(source_file)] = line_coverage

    files: dict[str, float] = {}
    warnings: list[str] = []
    total_changed = 0
    total_covered = 0

    for path, changed_lines in diff_data.items():
        normalized_path = _normalise_lcov_path(path)
        if normalized_path not in normalized_lcov:
            files[path] = 0.0
            warnings.append(f"No coverage data for {path}")
            total_changed += len(changed_lines)
            continue
        covered_lines_by_file = normalized_lcov[normalized_path]
        measured_lines: list[int] = [
            line_number
            for line_number in changed_lines
            if line_number in covered_lines_by_file
        ]
        if not measured_lines:
            files[path] = 0.0 if changed_lines else 1.0
            continue
        covered = sum(1 for line_number in measured_lines if covered_lines_by_file[line_number])
        ratio = covered / len(measured_lines)
        files[path] = round(ratio, 4)
        total_changed += len(measured_lines)
        total_covered += covered

    overall = (total_covered / total_changed) if total_changed > 0 else 1.0

    return PatchCoverageReport(
        files=files,
        overall_ratio=round(overall, 4),
        warnings=warnings,
        measured_lines=total_changed,
        covered_lines=total_covered,
    )


def evaluate_patch_gate(coverage: dict[str, float], threshold: float) -> list[str]:
    """Return files whose patch coverage falls below ``threshold``.

    Args:
        coverage: Mapping of file path to patch coverage ratio (0.0 to 1.0).
        threshold: Minimum acceptable ratio expressed as a fraction.

    Returns:
        Files below ``threshold`` in input (insertion) order. Empty list when
        every file meets or exceeds the threshold.
    """
    # @spec FR-004: evaluate_patch_gate isolates the threshold logic from the parser.
    # @spec AC-007: Threshold is optional; callers only invoke when it is configured.
    return [path for path, ratio in coverage.items() if ratio < threshold]


def summarise_patch_coverage(
    report: PatchCoverageReport,
    *,
    threshold: float | None = None,
) -> str:
    """Render a ``/spec.test``-friendly summary for a patch coverage report.

    Args:
        report: Computed patch coverage data.
        threshold: Optional gating threshold; when provided, failing files are listed.

    Returns:
        Multi-line summary string describing the patch coverage outcome.
    """
    # @spec AC-009: /spec.test summary surfaces patch coverage alongside total coverage.
    # @spec FR-005: Auto-integration is built on this pure formatter so the runner stays untouched.
    if not report.files and report.measured_lines == 0:
        return "Patch coverage: not applicable (no changed lines)."

    lines: list[str] = []
    overall_pct = report.overall_ratio * 100
    lines.append(
        f"Patch coverage: {overall_pct:.1f}% "
        f"({report.covered_lines}/{report.measured_lines} changed lines covered)"
    )

    if threshold is not None:
        threshold_pct = threshold * 100
        failing = evaluate_patch_gate(report.files, threshold)
        if failing:
            lines.append(f"Gate FAILED — threshold {threshold_pct:.0f}%:")
            for path in failing:
                lines.append(f"  - {path}: {report.files[path] * 100:.1f}% < {threshold_pct:.0f}%")
        else:
            lines.append(f"Gate PASSED — all files ≥ {threshold_pct:.0f}%.")

    for warning in report.warnings:
        lines.append(f"warning: {warning}")

    return "\n".join(lines)


def git_diff(base_ref: str = "HEAD~1", *, project_root: Path | None = None) -> str:
    """Run ``git diff`` and return unified diff text.

    Args:
        base_ref: Git revision to diff against.
        project_root: Optional repository root used as the subprocess working directory.

    Returns:
        Unified diff text, or an empty string when ``git`` is unavailable.
    """
    cwd = project_root or Path.cwd()
    try:
        # Use ``git diff --unified=0`` so patch coverage measures only the actual changed lines.
        completed = subprocess.run(
            ["git", "diff", "--unified=0", base_ref],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        return completed.stdout
    except FileNotFoundError:
        # Returning an empty diff lets callers degrade gracefully on machines without git.
        return ""
