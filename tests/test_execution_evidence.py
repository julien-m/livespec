"""Execution evidence requires real fresh subprocess results and reviewed assertions."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

import pytest

from tests.execution_evidence_support import AC, FEATURE, run
from tests.execution_evidence_support import project as project
from validator.drivers.runner import run_capability
from validator.drivers.schemas import DriverCapability, DriverManifest
from validator.execution_evidence import verify_execution_receipt
from validator.execution_mapping import ingest_mapping_review, prepare_mapping_review
from validator.execution_reports import parse_report
from validator.execution_scope import digest


def test_real_pytest_proves_only_reviewed_acceptance(project: Path) -> None:
    path = run(project)
    result = verify_execution_receipt(path, project, FEATURE, (AC,))
    assert result.valid, result.gaps
    assert result.certified_acs == [AC]
    assert result.acceptance_result_count == 1
    assert result.executed_tests[0].assertion_count == 1
    assert not verify_execution_receipt(path, project, FEATURE, (f"{FEATURE}:AC-002",)).valid


@pytest.mark.parametrize("name", ["report", "stdout", "capture.json", "receipt.json"])
def test_replaced_capture_bytes_are_rejected(project: Path, name: str) -> None:
    path = run(project)
    target = path.parent / name
    target.unlink()
    target.write_text("{}")
    assert not verify_execution_receipt(path, project, FEATURE).valid


def test_stale_existing_report_does_not_count(project: Path) -> None:
    (project / "old.xml").write_text(
        '<testsuite><testcase classname="test_app" name="test_add"/></testsuite>'
    )
    path = run(project, f"{shlex.quote(sys.executable)} -c pass")
    assert not verify_execution_receipt(path, project, FEATURE).valid


@pytest.mark.parametrize(
    "report",
    [
        "<testsuite/>",
        '<testsuite><testcase classname="test_app" name="test_add">'
        "<skipped/></testcase></testsuite>",
    ],
)
def test_empty_and_all_skipped_results_are_not_execution_proof(project: Path, report: str) -> None:
    code = (
        "import os; from pathlib import Path; "
        f"Path(os.environ['LIVESPEC_EXECUTION_REPORT']).write_text({report!r})"
    )
    path = run(project, f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}")
    assert not verify_execution_receipt(path, project, FEATURE).valid


def test_unreviewed_boolean_cannot_certify_mapping(project: Path) -> None:
    (project / "acceptance-review.json").write_text('{"reviewed": true}')
    assert not verify_execution_receipt(run(project), project, FEATURE).valid


def test_changed_mapping_cannot_reuse_old_raw_review(project: Path) -> None:
    mapping = json.loads((project / "mapping.json").read_text())
    mapping["bindings"][0]["expected"] = "Delete all files"
    (project / "mapping.json").write_text(json.dumps(mapping))
    assert not verify_execution_receipt(run(project), project, FEATURE).valid


def test_nonzero_exit_never_certifies(project: Path) -> None:
    (project / "app.py").write_text("def add(a, b):\n    return 0\n")
    assert not verify_execution_receipt(run(project), project, FEATURE).valid


def test_unsupported_driver_still_runs_without_certification(project: Path) -> None:
    driver = DriverManifest(
        name="custom", snapshots=DriverCapability(command=f"{sys.executable} -c pass")
    )
    result = run_capability(driver, "snapshots", project_root=project, feature=FEATURE)
    assert result.ok
    assert result.execution_receipt_path is None
    assert result.certification_gaps


def test_pytest_json_requires_an_executed_call() -> None:
    with pytest.raises(ValueError, match="executed call"):
        parse_report(b'{"tests":[{"nodeid":"a","outcome":"passed"}]}', "pytest-json")


def test_duplicate_results_are_ambiguous() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        parse_report(b'<testsuite><testcase name="a"/><testcase name="a"/></testsuite>', "junit")


def test_valid_forged_report_from_custom_command_is_noncertifying(project: Path) -> None:
    report = '<testsuite><testcase classname="test_app" name="test_add"/></testsuite>'
    code = (
        "import os; from pathlib import Path; "
        f"Path(os.environ['LIVESPEC_EXECUTION_REPORT']).write_text({report!r})"
    )
    path = run(project, f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}")
    result = verify_execution_receipt(path, project, FEATURE)
    assert not result.valid
    assert any("Unsupported runner" in gap for gap in result.gaps)


def test_real_pytest_all_skipped_reports_no_passing_execution(project: Path) -> None:
    (project / "test_app.py").write_text(
        'import pytest\n\ndef test_add():\n    pytest.skip("unavailable")\n'
    )
    result = verify_execution_receipt(run(project), project, FEATURE)
    assert not result.valid
    assert any("No passing" in gap for gap in result.gaps)
    assert result.executed_tests[0].status == "skipped"


def _rebind_assertion(project: Path, source: str, line: int) -> None:
    path = project / "test_app.py"
    path.write_text(source)
    mapping_path = project / "mapping.json"
    mapping = json.loads(mapping_path.read_text())
    mapping["bindings"][0].update(
        source_sha256=digest(path.read_bytes()), start_line=line, end_line=line
    )
    mapping_path.write_text(json.dumps(mapping))
    prepared = prepare_mapping_review(project, FEATURE, mapping_path)
    review_path = project / "acceptance-review.json"
    raw = json.loads(json.loads(review_path.read_text())["raw_results"][0])
    raw["reviewed_section_ids"] = [s.section_id for s in prepared.sections]
    section = next(s for s in prepared.sections if s.source == "test_app.py")
    raw["conclusions"][0]["plan_citations"][0]["section_id"] = section.section_id
    assert ingest_mapping_review(prepared, [json.dumps(raw)], review_path).ready


@pytest.mark.parametrize("branch", ["if False:", "def never_called():"])
def test_unexecuted_assertion_cannot_certify_a_passing_case(project: Path, branch: str) -> None:
    source = (
        f"from app import add\n\ndef test_add():\n    {branch}\n        assert add(1, 2) == 3\n"
    )
    _rebind_assertion(project, source, 5)
    result = verify_execution_receipt(run(project), project, FEATURE)
    assert not result.valid
    assert result.executed_tests[0].status == "passed"
    assert result.executed_tests[0].assertion_count == 0
    assert any("Unproven acceptance binding" in gap for gap in result.gaps)


def test_fake_pytest_named_executable_cannot_certify(project: Path) -> None:
    fake = project / "pytest-fake"
    fake.write_text(
        f"#!{sys.executable}\nimport os\nfrom pathlib import Path\n"
        "Path(os.environ['LIVESPEC_EXECUTION_REPORT']).write_text("
        '\'<testsuite><testcase classname="test_app" name="test_add"/></testsuite>\')\n'
    )
    fake.chmod(0o700)
    result = verify_execution_receipt(run(project, str(fake)), project, FEATURE)
    assert not result.valid
    assert any("Unsupported runner" in gap for gap in result.gaps)


def test_coverage_adapter_keeps_existing_required_report_guard(project: Path) -> None:
    driver = DriverManifest(
        name="pytest",
        coverage=DriverCapability(
            command=f"{sys.executable} -m pytest test_app.py -q",
            report_path="missing-lcov.info",
            report_adapter="junit",
            acceptance_mapping="mapping.json",
        ),
    )
    result = run_capability(driver, "coverage", project_root=project, feature=FEATURE)
    assert result.exit_code == 1
    assert "Missing coverage report" in result.stderr
    assert result.certification_gaps


def test_real_red_assertion_observation_does_not_certify_acceptance(project: Path) -> None:
    from validator.execution_evidence import verify_execution_observation

    (project / "app.py").write_text("def add(a, b):\n    return 0\n")
    path = run(project)
    result = verify_execution_observation(path, project, FEATURE, "red")
    assert result.valid, result.gaps
    assert result.certified_acs == []
    assert result.acceptance_result_count == 0
    assert result.executed_tests[0].status == "failed"
    assert result.executed_tests[0].assertion_count == 1
    assert not verify_execution_receipt(path, project, FEATURE).valid
    assert not verify_execution_observation(path, project, FEATURE, "passed").valid


def test_passed_observation_is_separate_from_acceptance_mapping(project: Path) -> None:
    from validator.execution_evidence import verify_execution_observation

    (project / "acceptance-review.json").write_text('{"reviewed":true}')
    path = run(project)
    result = verify_execution_observation(path, project, FEATURE, "passed")
    assert result.valid, result.gaps
    assert result.certified_acs == []
    assert not verify_execution_receipt(path, project, FEATURE).valid


@pytest.mark.parametrize(
    "source",
    [
        'def test_add():\n    raise AssertionError("not an assertion")\n',
        'def test_add():\n    raise RuntimeError("broken infrastructure")\n',
    ],
)
def test_failure_without_actual_assertion_cannot_prove_red(project: Path, source: str) -> None:
    from validator.execution_evidence import verify_execution_observation

    (project / "test_app.py").write_text(source)
    result = verify_execution_observation(run(project), project, FEATURE, "red")
    assert not result.valid
    assert any("actual assertion" in gap for gap in result.gaps)


def test_helper_assertion_cannot_impersonate_unexecuted_same_line_assertion(project: Path) -> None:
    source = (
        "from app import add\nfrom helper import check\ndef test_add():\n"
        "    if False:\n        assert add(1, 2) == 3\n    check()\n"
    )
    _rebind_assertion(project, source, 5)
    (project / "helper.py").write_text(
        "from app import add\n\ndef check():\n\n    assert add(1, 2) == 3\n"
    )
    (project / "conftest.py").write_text(
        'import pytest\npytest.register_assert_rewrite("helper")\n'
    )
    result = verify_execution_receipt(run(project), project, FEATURE)
    assert not result.valid
    assert result.executed_tests[0].status == "passed"
    assert result.executed_tests[0].assertion_count == 1
    assert any("Unproven acceptance binding" in gap for gap in result.gaps)


def test_expected_failure_xfail_is_not_an_observed_red_test(project: Path) -> None:
    from validator.execution_evidence import verify_execution_observation

    (project / "test_app.py").write_text(
        "import pytest\n\n@pytest.mark.xfail\ndef test_add():\n    assert False\n"
    )
    result = verify_execution_observation(run(project), project, FEATURE, "red")
    assert not result.valid
    assert result.executed_tests[0].status == "skipped"


def test_real_red_receipt_stays_observation_at_goal_and_archive_boundaries(project: Path) -> None:
    from validator.evidence_policy import EVIDENCE_POLICY_VERSION, typed_evidence_missing
    from validator.execution_evidence import verify_execution_observation
    from validator.run_receipts import recheck_receipts, verify_evidence_receipts

    (project / "app.py").write_text("def add(a, b):\n    return 0\n")
    path = run(project)
    contract = {"feature": FEATURE, "evidence_policy_version": EVIDENCE_POLICY_VERSION}
    evidence = {"execution_receipt_path": str(path)}
    red_task = {"evidence_kind": "execution", "evidence_expected_outcome": "red"}
    normal_task = {"evidence_kind": "execution"}
    assert not typed_evidence_missing(red_task, evidence, contract=contract, project_root=project)
    assert typed_evidence_missing(normal_task, evidence, contract=contract, project_root=project)

    checks = verify_evidence_receipts(
        [
            {**red_task, "accepted_evidence": evidence},
            {**normal_task, "accepted_evidence": evidence},
        ],
        project_root=project,
        feature=FEATURE,
    )
    assert len(checks) == 2
    assert checks[0].verified and checks[0].expected_outcome == "red"
    assert not checks[1].verified
    archived = checks[0].to_dict()
    assert archived["expected_outcome"] == "red"
    assert "certified_acs" not in archived
    assert recheck_receipts([archived], project_root=project, feature=FEATURE)[0].verified
    assert not recheck_receipts(
        [{**archived, "expected_outcome": ""}], project_root=project, feature=FEATURE
    )[0].verified
    observed = verify_execution_observation(path, project, FEATURE, "red")
    assert observed.valid and observed.certified_acs == []
    assert observed.acceptance_result_count == 0
