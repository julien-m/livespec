"""RED/GREEN regression proof from runner-owned execution receipts (feature 084 FR-005)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ..execution_capture import ExecutionCapture
from ..execution_evidence import _inspect  # pyright: ignore[reportPrivateUsage]
from ..execution_reports import ExecutedAssertion, ExecutedTest, junit_test_id
from .diff import is_traceability_artifact
from .models import FallbackReason


@dataclass(frozen=True)
class ObservedRun:
    """A verified capture with its failed and passed test identities."""

    receipt: Path
    capture: ExecutionCapture
    failed_assertions: dict[str, str]
    passed_tests: frozenset[str]


def is_test_file(path: str) -> bool:
    """Return True for test sources: a `tests`/`test` directory, test_*.py, *_test.py, conftest."""
    parts = PurePosixPath(path).parts
    name = parts[-1] if parts else ""
    return (
        any(part in ("tests", "test") for part in parts[:-1])
        or (name.startswith("test_") and name.endswith(".py"))
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


def test_command(capture: ExecutionCapture) -> list[str]:
    """Return the captured argv without the per-invocation report locations the runner adds."""
    injected = ("--junitxml=", "--junit-xml=", "--json-report-file=")
    return [arg for arg in capture.argv if not arg.startswith(injected)]


def _ids(test_id: str) -> tuple[str, str]:
    return test_id, junit_test_id(test_id)


def _failed_assertions(
    root: Path, tests: list[ExecutedTest], assertions: list[ExecutedAssertion]
) -> dict[str, str]:
    """Map node ids failing by an observed assertion to their test file (project-relative)."""
    failed_reports = {test.test_id for test in tests if test.status == "failed"}
    result: dict[str, str] = {}
    for item in assertions:
        if item.status == "failed" and failed_reports.intersection(_ids(item.test_id)):
            path = Path(item.path)
            result[item.test_id] = (
                path.relative_to(root).as_posix() if path.is_absolute() else path.as_posix()
            )
    return result


# @spec FR-005: Historical RED observation
#   — .specs/features/084-bugfix-lane/spec.md#fr-005
def observe(
    root: Path, feature: str, receipt: Path, expected: str
) -> tuple[ObservedRun | None, list[str]]:
    """Verify one receipt as RED (historical) or GREEN (current); return run and gaps.

    RED drops only the current-source comparison (plan D-02): later corrections must
    not invalidate the proof that the test failed before them.
    """
    try:
        inspection = _inspect(
            receipt.absolute(), root, feature, "2", require_current=expected == "green"
        )
    except (OSError, ValueError, ET.ParseError, SyntaxError) as exc:
        return None, [f"Invalid execution evidence: {exc}"]
    capture, tests = inspection.capture, inspection.tests
    gaps = list(inspection.gaps)
    failed = _failed_assertions(root, tests, inspection.assertions)
    passed = frozenset(test.test_id for test in tests if test.status == "passed")
    if expected == "red" and (capture.exit_code != 1 or not failed):
        gaps.append("Expected red: exit 1 with an observed failing assertion")
    if expected == "green" and (
        capture.exit_code != 0 or not passed or any(t.status == "failed" for t in tests)
    ):
        gaps.append("Expected green: exit 0, a passed test and no failed test")
    return ObservedRun(receipt, capture, failed, passed), gaps


def _changed_inputs(red: ExecutionCapture, green: ExecutionCapture) -> set[str]:
    keys = red.after.keys() | green.after.keys()
    return {
        key.removesuffix("@symlink") for key in keys if red.after.get(key) != green.after.get(key)
    }


# @spec FR-005: Regression, identity, order and changed inputs
#   — .specs/features/084-bugfix-lane/spec.md#fr-005
def regression_reasons(
    red: ObservedRun, green: ObservedRun, diff_paths: set[str] | None
) -> tuple[list[str], list[FallbackReason]]:
    """Return Regression tests and the reasons of AC-007 for a RED/GREEN pair."""
    regression = sorted(
        node for node in red.failed_assertions if green.passed_tests.intersection(_ids(node))
    )
    reasons: list[FallbackReason] = []
    if not regression:
        reasons.append(FallbackReason("no_regression_test", "no test failed in RED and passed"))
    test_files = {red.failed_assertions[node] for node in regression}
    for path in sorted(test_files):
        before, after = red.capture.after.get(path), green.capture.after.get(path)
        if before is None or before != after:
            reasons.append(FallbackReason("regression_test_changed", path))
    if test_command(red.capture) != test_command(green.capture):
        reasons.append(FallbackReason("command_mismatch", "GREEN ran a different test command"))
    if red.capture.started_ns >= green.capture.started_ns:
        reasons.append(FallbackReason("receipt_order_invalid", "GREEN did not start after RED"))
    changed = _changed_inputs(red.capture, green.capture) - test_files
    return regression, reasons + _changed_input_reasons(changed, diff_paths)


def _changed_input_reasons(changed: set[str], diff_paths: set[str] | None) -> list[FallbackReason]:
    """The fix must be a non-test change inside the bugfix diff (plan D-04)."""
    reasons: list[FallbackReason] = []
    support = sorted(path for path in changed if is_test_file(path))
    if support:
        reasons.append(FallbackReason("test_support_changed", ", ".join(support)))
    outside = sorted(
        path
        for path in changed
        if diff_paths is not None and path not in diff_paths and not is_traceability_artifact(path)
    )
    if not changed:
        reasons.append(FallbackReason("fix_not_in_diff", "no input changed between RED and GREEN"))
    elif outside:
        detail = "changed outside diff: " + ", ".join(outside)
        reasons.append(FallbackReason("fix_not_in_diff", detail))
    return reasons
