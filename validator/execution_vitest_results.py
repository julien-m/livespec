"""Reconcile every selected Vitest test and matcher against independent JUnit results."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from .execution_reports import ExecutedAssertion, ExecutedTest
from .execution_scope import digest, read_regular

if TYPE_CHECKING:
    # Capture imports runner preparation; defer its type to avoid a runtime cycle.
    from .execution_capture import ExecutionCapture


class VitestTest(BaseModel):
    """Exact runner test identity and original source origin."""

    model_config = ConfigDict(extra="forbid", strict=True)
    test_id: str
    file: str
    full_name: str
    status: Literal["passed", "failed", "skipped"]


class VitestInventory(BaseModel):
    """Finalized complete selection with runner-observed integrity errors."""

    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: str
    invocation: str
    project_root: str
    feature: str
    tests: list[VitestTest]
    errors: list[str]
    bound_inputs: dict[str, str]


# @spec FR-002: Reconcile every selected test against settled actual matcher evidence
# — .specs/features/096-node-vitest-execution/spec.md#fr-002
def verify_vitest_results(
    capture: ExecutionCapture,
    directory: Path,
    root: Path,
    tests: list[ExecutedTest],
    assertions: list[ExecutedAssertion],
) -> None:
    """Reject missing, extra, mismatched, unsupported or unobserved selected results."""
    payload = read_regular(directory / "inventory", root)
    if digest(payload) != capture.vitest_inventory_sha256:
        raise ValueError("Vitest inventory changed")
    inventory = VitestInventory.model_validate_json(payload)
    if (
        inventory.schema_version != "1"
        or inventory.invocation != capture.invocation
        or inventory.project_root != str(root)
        or inventory.feature != capture.feature
    ):
        raise ValueError("Foreign Vitest inventory")
    if inventory.errors:
        raise ValueError("Unsupported Vitest observation: " + "; ".join(inventory.errors))
    for relative, expected in inventory.bound_inputs.items():
        candidate = root / relative
        if not candidate.is_relative_to(root) or ".." in Path(relative).parts:
            raise ValueError("Vitest loaded input escapes project")
        if digest(read_regular(candidate, root)) != expected:
            raise ValueError(f"Vitest loaded configuration/setup input changed: {relative}")
    if not inventory.bound_inputs:
        raise ValueError("Vitest has no bound loaded source inputs")
    actual = {test.test_id: test.status for test in tests}
    selected = {test.test_id: test.status for test in inventory.tests}
    if not selected or len(selected) != len(inventory.tests) or actual != selected:
        raise ValueError("Vitest/JUnit complete selected test inventory mismatch or zero tests")
    for test in inventory.tests:
        source = root / test.file
        if not source.is_relative_to(root) or ".." in Path(test.file).parts:
            raise ValueError("Vitest test source escapes project")
        if test.file not in inventory.bound_inputs or not source.is_file():
            raise ValueError("Vitest test source was not bound to invocation")
        observed = [item for item in assertions if item.test_id == test.test_id]
        if test.status != "skipped" and not observed:
            raise ValueError(f"No executed supported matcher for selected test {test.test_id}")
        if test.status == "skipped" and observed:
            raise ValueError("Skipped Vitest test has assertion evidence")
    for item in assertions:
        if item.test_id not in selected or item.path not in inventory.bound_inputs:
            raise ValueError("Vitest assertion has unbound test/source origin")
        source_text = read_regular(root / item.path, root).decode()
        if item.line > len(source_text.splitlines()):
            raise ValueError("Vitest assertion line is outside its source")
        if selected[item.test_id] == "passed" and item.status != "passed":
            raise ValueError("Passed Vitest test contains a failing matcher")
