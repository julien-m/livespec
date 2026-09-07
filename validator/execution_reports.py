"""Parse captured test results without inventing executed assertion counts."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExecutedTest(BaseModel):
    """One observed test outcome; unknown assertion counts remain null."""

    model_config = ConfigDict(extra="forbid")
    test_id: str = Field(min_length=1)
    status: Literal["passed", "failed", "skipped"]
    assertion_count: int | None = Field(default=None, ge=0)


def parse_report(content: bytes, adapter: str) -> list[ExecutedTest]:
    """Parse immutable JUnit or pytest-json-report bytes, rejecting ambiguity."""
    if adapter == "junit":
        if b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
            raise ValueError("XML declarations are unsupported")
        root = ET.fromstring(content)
        if root.tag not in {"testsuites", "testsuite"}:
            raise ValueError("Expected JUnit testsuite(s)")
        tests = [_junit_test(case) for case in root.iter("testcase")]
    elif adapter == "pytest-json":
        data = json.loads(content)
        if not isinstance(data, dict) or not isinstance(data.get("tests"), list):
            raise ValueError("Expected pytest JSON tests")
        tests = [_pytest_test(case) for case in data["tests"]]
    else:
        raise ValueError(f"Unsupported report adapter: {adapter}")
    if len({test.test_id for test in tests}) != len(tests):
        raise ValueError("Ambiguous duplicate test identities")
    return tests


def _junit_test(case: ET.Element) -> ExecutedTest:
    test_id = "::".join(filter(None, (case.get("classname"), case.get("name"))))
    status: Literal["passed", "failed", "skipped"] = "passed"
    if case.find("failure") is not None or case.find("error") is not None:
        status = "failed"
    elif case.find("skipped") is not None:
        status = "skipped"
    # JUnit reports cases, not individual assertion execution. Even an optional
    # assertions attribute cannot establish the expected acceptance behavior.
    return ExecutedTest(test_id=test_id, status=status)


def _pytest_test(case: object) -> ExecutedTest:
    if not isinstance(case, dict):
        raise ValueError("Expected pytest test object")
    outcome = case.get("outcome")
    if outcome not in {"passed", "failed", "skipped"}:
        raise ValueError("Unsupported pytest outcome")
    call = case.get("call")
    if outcome == "passed" and (not isinstance(call, dict) or call.get("outcome") != "passed"):
        raise ValueError("Passing pytest case lacks executed call")
    return ExecutedTest.model_validate({"test_id": case.get("nodeid"), "status": outcome})


class ExecutedAssertion(BaseModel):
    """One actual pytest passing-assertion callback, bound to its executing test."""

    model_config = ConfigDict(extra="forbid", strict=True)
    test_id: str
    path: str
    line: int = Field(ge=1)
    assertion: str = Field(min_length=1)
    status: Literal["passed", "failed"] = "passed"


class AssertionTrace(BaseModel):
    """Invocation-owned actual assertion observations, not inferred AST nodes."""

    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: str
    invocation: str
    project_root: str
    feature: str
    assertions: list[ExecutedAssertion]


def junit_test_id(nodeid: str) -> str:
    """Translate pytest's node identity into its default JUnit case identity."""
    parts = nodeid.split("::")
    module = parts[0].removesuffix(".py").replace("/", ".")
    return ".".join([module, *parts[1:-1]]) + "::" + parts[-1]
