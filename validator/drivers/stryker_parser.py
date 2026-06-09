# LiveSpec traceability anchors
# @spec(FR-003)

"""Parse Stryker mutation reports into structured results."""

# @spec FR-003: Stryker JSON report parser
# — .specs/features/018-driver-typescript-javascript/spec.md#fr-003

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict, cast

# Stryker mutation-report-schema status names. ``Killed`` / ``Survived`` /
# ``Timeout`` / ``NoCoverage`` are the four buckets the driver tracks; other
# statuses (``CompileError``, ``RuntimeError``, ``Ignored``) are out of scope
# for the kill-rate computation per spec AC-010.
_KILLED_STATUS = "Killed"
_SURVIVED_STATUS = "Survived"
_TIMEOUT_STATUS = "Timeout"
_NO_COVERAGE_STATUS = "NoCoverage"


class StrykerParseResult(TypedDict):
    """Normalized Stryker summary used by the TS/JS driver."""

    killed: int
    survived: int
    timeout: int
    no_coverage: int
    kill_rate: float


def _empty_result() -> StrykerParseResult:
    """Return the default parse result used for missing or invalid reports."""
    return {
        "killed": 0,
        "survived": 0,
        "timeout": 0,
        "no_coverage": 0,
        "kill_rate": 0.0,
    }


def compute_kill_rate(killed: int, survived: int, timeout: int) -> float:
    """Compute the percentage of mutants neutralized by the test suite.

    Stryker treats both ``Killed`` and ``Timeout`` as kills for scoring
    purposes — surviving mutants are the only true gaps in the suite.

    Args:
        killed: Number of mutants explicitly killed by tests.
        survived: Number of mutants the suite failed to detect.
        timeout: Number of mutants that triggered a timeout (counted as kills).

    Returns:
        Kill rate as a percentage in the range ``0.0`` to ``100.0``.
    """
    total = killed + survived + timeout
    if total == 0:
        return 0.0
    return ((killed + timeout) / total) * 100.0


def _sum_from_files_block(files_block: dict[str, Any]) -> tuple[int, int, int, int]:
    """Aggregate mutant statuses across the ``files.<path>.mutants[]`` shape.

    Args:
        files_block: Mapping keyed by source path containing ``mutants`` lists.

    Returns:
        Tuple ``(killed, survived, timeout, no_coverage)``.
    """
    killed = 0
    survived = 0
    timeout = 0
    no_coverage = 0

    for file_entry_obj in files_block.values():  # type: ignore[union-attr]
        if not isinstance(file_entry_obj, dict):
            continue
        file_entry = cast(dict[str, Any], file_entry_obj)
        mutants_obj = file_entry.get("mutants", [])
        if not isinstance(mutants_obj, list):
            continue
        mutants = cast(list[Any], mutants_obj)
        for mutant_obj in mutants:
            if not isinstance(mutant_obj, dict):
                continue
            mutant = cast(dict[str, Any], mutant_obj)
            status = mutant.get("status")
            if status == _KILLED_STATUS:
                killed += 1
            elif status == _SURVIVED_STATUS:
                survived += 1
            elif status == _TIMEOUT_STATUS:
                timeout += 1
            elif status == _NO_COVERAGE_STATUS:
                no_coverage += 1

    return killed, survived, timeout, no_coverage


def _coerce_count(value: object) -> int:
    """Convert metric values to ints while treating invalid data as zero."""
    try:
        if isinstance(value, (int, float, str, bytes, bytearray)):
            return int(value)
        return 0
    except (TypeError, ValueError):
        return 0


def _sum_from_metrics_block(metrics_block: dict[str, Any]) -> tuple[int, int, int, int]:
    """Read mutant counts from the alternate ``metrics`` payload shape.

    Args:
        metrics_block: Mapping with ``killed`` / ``survived`` / ``timeout`` /
            ``noCoverage`` integer fields.

    Returns:
        Tuple ``(killed, survived, timeout, no_coverage)``.
    """
    killed = _coerce_count(metrics_block.get("killed", 0) or 0)  # type: ignore[union-attr]
    survived = _coerce_count(metrics_block.get("survived", 0) or 0)  # type: ignore[union-attr]
    timeout = _coerce_count(metrics_block.get("timeout", 0) or 0)  # type: ignore[union-attr]
    no_coverage = _coerce_count(metrics_block.get("noCoverage", 0) or 0)  # type: ignore[union-attr]
    return killed, survived, timeout, no_coverage


def parse_stryker_report(json_text: str | None) -> StrykerParseResult:
    """Parse a Stryker JSON report into a normalized result.

    Supports two report shapes:
    - ``files.<path>.mutants[].status`` (mutation-report-schema, default)
    - top-level ``metrics`` block (alternate slim format)

    Args:
        json_text: Raw JSON text or ``None`` when the report is missing.

    Returns:
        Structured killed/survived/timeout/no_coverage counts and kill rate.
    """
    if not json_text:
        return _empty_result()

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return _empty_result()

    if not isinstance(data, dict):
        return _empty_result()

    data_typed = cast(dict[str, Any], data)
    files_block_obj = data_typed.get("files")
    if isinstance(files_block_obj, dict) and files_block_obj:
        files_block = cast(dict[str, Any], files_block_obj)
        killed, survived, timeout, no_coverage = _sum_from_files_block(files_block)
    else:
        metrics_block_obj = data_typed.get("metrics")
        if isinstance(metrics_block_obj, dict):
            metrics_block = cast(dict[str, Any], metrics_block_obj)
            killed, survived, timeout, no_coverage = _sum_from_metrics_block(metrics_block)
        else:
            return _empty_result()

    return {
        "killed": killed,
        "survived": survived,
        "timeout": timeout,
        "no_coverage": no_coverage,
        "kill_rate": compute_kill_rate(killed, survived, timeout),
    }


def load_stryker_report(report_path: Path) -> StrykerParseResult:
    """Load and parse a Stryker JSON report from disk.

    Args:
        report_path: Path to ``reports/mutation/mutation.json`` (Stryker default).

    Returns:
        Structured parse result, or an empty result when the file cannot be read.
    """
    try:
        json_text = report_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return _empty_result()

    return parse_stryker_report(json_text)
