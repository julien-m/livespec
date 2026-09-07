"""The spec-test traceback guard distinguishes actual errors from recorded diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from validator.expectations import parse_expectations
from validator.verify_output import evaluate_rules

ROOT = Path(__file__).resolve().parents[1]
EXPECTATIONS = ROOT / ".agent-sync/skills/spec-test/expectations.md"
HEADER = "Traceback (most recent call last):\n"
DIAGNOSTIC = json.dumps(
    {
        "test_id": "test_traceback_guard_requires_an_actual_error_signature[Traceback-PASS]",
        "status": "passed",
        "citation": 'assert "Traceback" not in result.output',
        "detail": repr(HEADER),
    }
)


@pytest.mark.parametrize(
    ("stdout", "stderr", "expected"),
    [
        (DIAGNOSTIC, "", "PASS"),
        ("", DIAGNOSTIC, "PASS"),
        (HEADER + '  File "runner.py", line 1\nValueError: broken\n', "", "FAIL"),
        (DIAGNOSTIC, HEADER + "RuntimeError: broken\n", "FAIL"),
    ],
)
def test_spec_test_guard_preserves_diagnostics_and_rejects_real_tracebacks(
    stdout: str, stderr: str, expected: str
) -> None:
    """Apply the actual command rule to successful diagnostics and actual error headers."""
    parsed = parse_expectations(EXPECTATIONS)
    rule = next(rule for rule in parsed.verify.must_not if "Traceback" in str(rule.payload))
    report = evaluate_rules(
        {"must_not": [{"verb": rule.verb, "kind": rule.kind, "payload": rule.payload}]},
        artifact={"exit_code": 0, "stdout": stdout, "stderr": stderr},
        active_flags=[],
        feature=None,
        project_root=ROOT,
    )
    assert rule.payload == HEADER
    assert report.rules[0].status == expected


@pytest.mark.parametrize("needle", ["Traceback", "citation"])
def test_archived_literal_rule_keeps_its_original_meaning(needle: str) -> None:
    """An old embedded rule stays literal even after current expectations are corrected."""
    rules = {"must_not": [{"verb": "must_not", "kind": "contains", "payload": needle}]}
    artifact = {
        "exit_code": 0,
        "stdout": DIAGNOSTIC,
        "stderr": "",
    }
    original = json.dumps({"artifact": artifact, "verify_rules": rules}, sort_keys=True)
    report = evaluate_rules(
        rules,
        artifact=artifact,
        active_flags=[],
        feature=None,
        project_root=ROOT,
    )
    assert report.rules[0].status == "FAIL" and report.outcome == "drift"
    assert json.dumps({"artifact": artifact, "verify_rules": rules}, sort_keys=True) == original
