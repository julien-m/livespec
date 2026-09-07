"""Structured runner outcomes distinguish collection failures from diagnostic mentions."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

import pytest

from tests.execution_evidence_support import AC, FEATURE, run
from tests.execution_evidence_support import project as project
from validator.evidence_policy import typed_evidence_missing
from validator.execution_evidence import verify_execution_receipt
from validator.expectations import parse_expectations
from validator.verify_output import evaluate_rules

ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTIC = json.dumps({"status": "passed", "rationale": "The ERROR collecting guard was kept."})


def _configure_case(project: Path, case: str) -> None:
    # Use actual pytest collection/session hooks, never a fabricated result report.
    if case in ("collection", "collection-exit-zero"):
        (project / "test_app.py").write_text("def test_broken(:\n    pass\n")
    elif case == "empty":
        (project / "test_app.py").write_text("# No executable tests.\n")
    elif case == "failed":
        (project / "app.py").write_text("def add(a, b):\n    return 0\n")
    elif case == "diagnostic":
        (project / "app.py").write_text(
            "def add(a, b):\n"
            '    print("ERROR collecting: documented sample; Traceback")\n'
            "    return a + b\n"
        )
    if case == "collection-exit-zero":
        (project / "conftest.py").write_text(
            "def pytest_sessionfinish(session):\n    session.exitstatus = 0\n"
        )
    elif case == "missing-report":
        (project / "conftest.py").write_text(
            "import os\nfrom pathlib import Path\ndef pytest_unconfigure():\n"
            '    Path(os.environ["LIVESPEC_EXECUTION_REPORT"]).unlink(missing_ok=True)\n'
        )


@pytest.mark.parametrize(
    ("case", "exit_code", "gap"),
    [
        ("collection", 2, "Report contains failed tests"),
        ("collection-exit-zero", 0, "Report contains failed tests"),
        ("empty", 5, "No passing executed test results"),
        ("failed", 1, "Report contains failed tests"),
        ("missing-report", 0, "Invalid execution evidence"),
        ("diagnostic", 0, ""),
    ],
)
def test_policy2_uses_actual_runner_results_instead_of_error_words(
    project: Path, case: str, exit_code: int, gap: str
) -> None:
    """Refuse failed/absent results even at exit zero; permit words in successful output."""
    _configure_case(project, case)
    receipt = run(project, f"{shlex.quote(sys.executable)} -m pytest test_app.py -q -s")
    capture = json.loads((receipt.parent / "capture.json").read_text())
    assert capture["exit_code"] == exit_code
    result = verify_execution_receipt(receipt, project, FEATURE, (AC,), evidence_policy="2")
    missing = typed_evidence_missing(
        {"evidence_kind": "execution", "required_acs": [AC]},
        {"execution_receipt_path": str(receipt)},
        contract={"evidence_policy_version": "2", "feature": FEATURE},
        project_root=project,
    )
    assert result.valid is (not gap)
    if gap:
        assert any(gap in detail for detail in result.gaps)
        assert missing and result.certified_acs == []
    else:
        assert missing == [] and result.certified_acs == [AC]
        assert "ERROR collecting" in (receipt.parent / "stdout").read_text()


def test_current_spec_test_accepts_collection_error_words_in_review_json() -> None:
    """Current documentary stdout can quote diagnostics without claiming an execution failure."""
    parsed = parse_expectations(ROOT / ".agent-sync/skills/spec-test/expectations.md")
    rules = {
        "must_not": [
            {"verb": rule.verb, "kind": rule.kind, "payload": rule.payload}
            for rule in parsed.verify.must_not
        ]
    }
    report = evaluate_rules(
        rules,
        artifact={"exit_code": 0, "stdout": DIAGNOSTIC, "stderr": ""},
        active_flags=[],
        feature=None,
        project_root=ROOT,
    )
    assert all(rule.status == "PASS" for rule in report.rules)


def test_old_collection_word_rule_remains_literal_and_drift() -> None:
    """Changing the current sidecar never rewrites an old embedded contains rule."""
    rules = {"must_not": [{"verb": "must_not", "kind": "contains", "payload": "ERROR collecting"}]}
    artifact = {"exit_code": 0, "stdout": DIAGNOSTIC, "stderr": ""}
    original = json.dumps({"rules": rules, "artifact": artifact}, sort_keys=True)
    report = evaluate_rules(
        rules, artifact=artifact, active_flags=[], feature=None, project_root=ROOT
    )
    assert report.outcome == "drift" and report.rules[0].status == "FAIL"
    assert json.dumps({"rules": rules, "artifact": artifact}, sort_keys=True) == original
