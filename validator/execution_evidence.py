"""Independently consume runner captures and current acceptance evidence."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .acceptance_requirements import execution_acceptance_ids
from .execution_capture import ExecutionCapture
from .execution_mapping import AcceptanceMapping, certify_mappings
from .execution_reports import (
    AssertionTrace,
    ExecutedAssertion,
    ExecutedTest,
    junit_test_id,
    parse_report,
)
from .execution_runner import runner_provenance
from .execution_scope import EXECUTION_SCOPE_POLICY, digest, read_regular, source_manifest


class ExecutionReceipt(BaseModel):
    """A reference to runner-owned capture; caller verdict fields are forbidden."""

    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: str
    invocation: str
    capture_sha256: str


class EvidenceVerification(BaseModel):
    """Current proven scope and actionable gaps; no inferred AC success."""

    valid: bool
    certified_acs: list[str]
    gaps: list[str]
    executed_tests: list[ExecutedTest] = []
    acceptance_result_count: int = 0


@dataclass
class _Inspection:
    capture: ExecutionCapture
    tests: list[ExecutedTest]
    assertions: list[ExecutedAssertion]
    gaps: list[str]


def verify_execution_receipt(
    path: Path,
    project_root: Path,
    feature: str,
    required_acs: tuple[str, ...] = (),
    *,
    evidence_policy: Literal["1", "2"] = "2",
) -> EvidenceVerification:
    """Require real passing assertions, current raw review and justified AC mappings."""
    try:
        if evidence_policy not in ("1", "2"):
            raise ValueError("Unsupported execution evidence policy")
        return _verify(
            path, project_root.resolve(strict=True), feature, required_acs, evidence_policy
        )
    except (OSError, ValueError, ET.ParseError, SyntaxError) as exc:
        return _invalid(exc)


def verify_execution_observation(
    path: Path,
    project_root: Path,
    feature: str,
    expected_outcome: Literal["red", "passed"],
    *,
    evidence_policy: Literal["1", "2"] = "2",
) -> EvidenceVerification:
    """Verify an explicitly expected RED/PASS observation without certifying any AC."""
    try:
        if expected_outcome not in ("red", "passed"):
            raise ValueError("Unsupported expected execution outcome")
        root = project_root.resolve(strict=True)
        inspection = _inspect(path, root, feature, evidence_policy)
        capture, tests, assertions, gaps = (
            inspection.capture,
            inspection.tests,
            inspection.assertions,
            inspection.gaps,
        )
        status = "failed" if expected_outcome == "red" else "passed"
        expected_code = 1 if expected_outcome == "red" else 0
        matching_tests = {test.test_id for test in tests if test.status == status}
        observed = any(
            item.status == status
            and matching_tests.intersection((item.test_id, junit_test_id(item.test_id)))
            for item in assertions
        )
        if capture.exit_code != expected_code or not observed:
            gaps.append(f"Expected {expected_outcome} actual assertion execution was not observed")
        if expected_outcome == "passed" and any(test.status == "failed" for test in tests):
            gaps.append("Report contains failed tests")
        if capture.after != source_manifest(root, feature):
            gaps.append("Inputs changed during observation verification")
        return EvidenceVerification(
            valid=not gaps, certified_acs=[], gaps=gaps, executed_tests=tests
        )
    except (OSError, ValueError, ET.ParseError, SyntaxError) as exc:
        return _invalid(exc)


def _invalid(exc: Exception) -> EvidenceVerification:
    return EvidenceVerification(
        valid=False, certified_acs=[], gaps=[f"Invalid execution evidence: {exc}"]
    )


def _read_capture(path: Path, root: Path, feature: str) -> tuple[ExecutionCapture, Path]:
    receipt = ExecutionReceipt.model_validate_json(read_regular(path, root))
    if (
        receipt.schema_version != "1"
        or len(receipt.invocation) != 32
        or any(char not in "0123456789abcdef" for char in receipt.invocation)
    ):
        raise ValueError("Unsupported execution receipt identity")
    directory = root / ".specs/.execution" / receipt.invocation
    if path.absolute() != directory / "receipt.json":
        raise ValueError("Receipt is not at its runner-owned location")
    payload = read_regular(directory / "capture.json", root)
    if digest(payload) != receipt.capture_sha256:
        raise ValueError("Runner capture changed")
    capture = ExecutionCapture.model_validate_json(payload)
    if (
        capture.schema_version != "1"
        or capture.scope_policy_version != EXECUTION_SCOPE_POLICY
        or capture.project_root != str(root)
        or capture.feature != feature
        or capture.invocation != receipt.invocation
    ):
        raise ValueError("Foreign project, feature or invocation")
    if capture.started_ns > capture.finished_ns or not capture.argv:
        raise ValueError("Invalid invocation lifetime")
    directory_stat = directory.stat(follow_symlinks=False)
    if capture.directory_identity != (directory_stat.st_dev, directory_stat.st_ino):
        raise ValueError("Runner directory replaced")
    return capture, directory


def _read_results(
    capture: ExecutionCapture, directory: Path, root: Path
) -> tuple[list[ExecutedTest], list[ExecutedAssertion]]:
    captured_bytes: dict[str, bytes] = {}
    for name, expected in (
        ("stdout", capture.stdout_sha256),
        ("stderr", capture.stderr_sha256),
        ("report", capture.report_sha256),
    ):
        captured_bytes[name] = read_regular(directory / name, root)
        if digest(captured_bytes[name]) != expected:
            raise ValueError(f"Captured {name} changed")
    report_stat = (directory / "report").stat(follow_symlinks=False)
    if capture.report_identity != (report_stat.st_dev, report_stat.st_ino):
        raise ValueError("Captured report was replaced")
    tests = parse_report(captured_bytes["report"], capture.report_adapter)
    if not capture.assertion_trace_sha256:
        return tests, []
    trace_bytes = read_regular(directory / "assertions", root)
    if digest(trace_bytes) != capture.assertion_trace_sha256:
        raise ValueError("Assertion trace changed")
    trace = AssertionTrace.model_validate_json(trace_bytes)
    if (
        trace.schema_version != "1"
        or trace.invocation != capture.invocation
        or trace.project_root != str(root)
        or trace.feature != capture.feature
    ):
        raise ValueError("Foreign assertion execution trace")
    for test in tests:
        test.assertion_count = sum(
            test.test_id in (item.test_id, junit_test_id(item.test_id)) for item in trace.assertions
        )
    return tests, trace.assertions


def _inspect(
    path: Path, root: Path, feature: str, evidence_policy: Literal["1", "2"]
) -> _Inspection:
    if evidence_policy not in ("1", "2"):
        raise ValueError("Unsupported execution evidence policy")
    capture, directory = _read_capture(path, root, feature)
    gaps = list(capture.gaps)
    if capture.acceptance_evidence_policy not in ("1", "2"):
        gaps.append("Unsupported runner acceptance evidence policy")
    if evidence_policy == "2" and capture.acceptance_evidence_policy != "2":
        gaps.append("Runner capture does not declare current acceptance evidence policy 2")
    if capture.runner_provenance != runner_provenance():
        gaps.append("Trusted runner provenance changed or missing")
    if capture.before != capture.after or capture.after != source_manifest(root, feature):
        gaps.append("Source, test or configuration inputs are stale")
    tests, assertions = _read_results(capture, directory, root)
    if not capture.assertion_trace_sha256:
        gaps.append("No actual assertion execution trace")
    return _Inspection(capture, tests, assertions, gaps)


def _passing_result_gaps(capture: ExecutionCapture, tests: list[ExecutedTest]) -> list[str]:
    """Keep process failure and observed test-result gaps independent of acceptance types."""
    gaps: list[str] = []
    if capture.exit_code != 0:
        gaps.append(f"Execution exited {capture.exit_code}")
    if not tests or not any(test.status == "passed" for test in tests):
        gaps.append("No passing executed test results")
    if any(test.status == "failed" for test in tests):
        gaps.append("Report contains failed tests")
    return gaps


def _verify(
    path: Path,
    root: Path,
    feature: str,
    required: tuple[str, ...],
    evidence_policy: Literal["1", "2"],
) -> EvidenceVerification:
    inspection = _inspect(path, root, feature, evidence_policy)
    capture, tests, assertions, gaps = (
        inspection.capture,
        inspection.tests,
        inspection.assertions,
        inspection.gaps,
    )
    gaps.extend(_passing_result_gaps(capture, tests))
    spec = read_regular(root / f".specs/features/{feature}/spec.md", root).decode()
    if evidence_policy == "2" and set(required) - set(
        execution_acceptance_ids(root, feature, spec_text=spec)
    ):
        gaps.append("Required acceptance does not declare execution evidence")
    certified: list[str] = []
    if capture.acceptance_mapping and not gaps:
        gaps.extend(_acceptance_input_gaps(capture, root))
    if capture.acceptance_mapping and not gaps:
        certified, mapping_gaps = certify_mappings(
            root,
            feature,
            root / capture.acceptance_mapping,
            tests,
            assertions,
            expected_inputs=capture.raw_after,
            expected_sources=capture.after,
            evidence_policy=evidence_policy,
        )
        gaps.extend(mapping_gaps)
        gaps.extend(_acceptance_input_gaps(capture, root))
    else:
        gaps.append("No verified acceptance assertion mapping")
    if capture.after != source_manifest(root, feature):
        gaps.append("Inputs changed while verifying acceptance evidence")
    missing = sorted(set(required) - set(certified))
    if missing:
        gaps.append("Unproven required acceptance: " + ", ".join(missing))
    return EvidenceVerification(
        valid=not gaps and bool(certified),
        certified_acs=certified if not gaps else [],
        gaps=gaps,
        executed_tests=tests,
        acceptance_result_count=len(certified) if not gaps else 0,
    )


def _acceptance_input_gaps(capture: ExecutionCapture, root: Path) -> list[str]:
    """Governed mapping and raw review remain inputs even inside generated caches."""
    if not capture.acceptance_mapping:
        return []
    mapping_path = root / capture.acceptance_mapping
    mapping_bytes = read_regular(mapping_path, root)
    mapping = AcceptanceMapping.model_validate_json(mapping_bytes)
    review_path = root / mapping.review_receipt_path
    gaps = []
    for path, current in (
        (mapping_path, mapping_bytes),
        (review_path, read_regular(review_path, root)),
    ):
        relative = path.relative_to(root).as_posix()
        previous = capture.raw_before.get(relative)
        if (
            previous is None
            or previous != capture.raw_after.get(relative)
            or previous != digest(current)
        ):
            gaps.append(f"Governed acceptance input changed or was not captured: {relative}")
    return gaps
