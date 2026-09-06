"""Automatic packaging of exact protocol-fixture reviewer output, never a real review claim."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_penflow_review_approval import FEATURE, ReviewProject, _read_json, _write_json
from tests.test_penflow_review_approval import project as project
from validator.penflow_approval_files import PenflowApprovalError, load_object
from validator.penflow_review_approval import require_approved_requirements
from validator.penflow_review_result import package_review_result


def _output(project: ReviewProject, snapshot: dict[str, object]) -> Path:
    path = project.root / "actual-protocol-fixture-output.json"
    _write_json(
        path,
        {
            "invocation_id": "protocol-fixture-invocation",
            "producer_id": "test-only-reviewer",
            "input_sha256": snapshot["input_sha256"],
            "verdict": "PASS",
            "blocking_count": 0,
            "findings": [],
        },
    )
    return path


def _cli(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", "from validator.cli import app; app()", *arguments],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )


@pytest.mark.parametrize("number", ["1e400", "-1e400", "NaN", "Infinity"])
def test_loader_rejects_nonfinite_values_before_use(number: str) -> None:
    with pytest.raises(PenflowApprovalError, match="nonfinite_json"):
        load_object(f'{{"assertion":{number}}}'.encode())


# @spec AC-008: actual response bytes are packaged, never synthesized
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#ac-008
def test_real_cli_packages_raw_output_then_existing_transition_accepts_it(
    project: ReviewProject,
) -> None:
    pipeline = project.spec.parent / "pipeline.md"
    pipeline.write_text("| Phase | Status |\n| Plan Review | Pending |\n| Implement | Pending |\n")
    snapshot = project.snapshot()
    output = _output(project, snapshot)
    original = output.read_bytes()
    result = _cli(
        project.root,
        "penflow-contract",
        "review-result",
        "--snapshot",
        snapshot["snapshot"]["path"],
        "--output",
        str(output),
        "--json",
    )
    assert result.returncode == 0, result.stderr + result.stdout
    packaged = json.loads(result.stdout)
    assert packaged["certified"] is False
    wrapper = _read_json(project.root / packaged["result"]["path"])
    archived = project.root / wrapper["review"]["output"]["path"]
    assert archived.read_bytes() == original
    assert "Pending" in pipeline.read_text() and not project.baseline.exists()
    output.unlink()  # Published authority uses immutable original output bytes.
    approved = _cli(
        project.root,
        "pipeline",
        "update",
        "--feature",
        FEATURE,
        "--phase",
        "plan-review",
        "--status",
        "done",
        "--review-result",
        packaged["result"]["path"],
    )
    assert approved.returncode == 0, approved.stderr + approved.stdout
    assert "| Implement | Pending |" in pipeline.read_text()
    require_approved_requirements(project.root, FEATURE)


@pytest.mark.parametrize(
    "field", ["verdict", "findings", "producer_id", "input_sha256", "blocking_count"]
)
def test_packaging_never_completes_missing_review_fields(
    project: ReviewProject, field: str
) -> None:
    snapshot = project.snapshot()
    output = _output(project, snapshot)
    value = _read_json(output)
    del value[field]
    _write_json(output, value)
    with pytest.raises(ValueError):
        package_review_result(project.root, Path(snapshot["snapshot"]["path"]), output)
    assert not list((project.root / ".specs/penflow-approvals").glob("review-result-*.json"))


@pytest.mark.parametrize("change", ["input", "unknown_requirement", "false_count", "forged_output"])
def test_packaging_rejects_contradictory_or_foreign_response(
    project: ReviewProject, change: str
) -> None:
    snapshot = project.snapshot()
    output = _output(project, snapshot)
    value = _read_json(output)
    if change == "input":
        value["input_sha256"] = "f" * 64
    elif change == "unknown_requirement":
        value["findings"] = [
            {"severity": "WARNING", "message": "Unknown", "requirement_ids": ["foreign:FR-001"]}
        ]
    elif change == "false_count":
        value["blocking_count"] = False
    else:
        value["output"] = {"path": "fake.json", "sha256": "f" * 64}
    _write_json(output, value)
    with pytest.raises(ValueError):
        package_review_result(project.root, Path(snapshot["snapshot"]["path"]), output)


def test_stale_sources_block_packaging_before_result_publication(project: ReviewProject) -> None:
    snapshot = project.snapshot()
    output = _output(project, snapshot)
    project.spec.write_text(project.spec.read_text().replace("display name", "phone number"))
    with pytest.raises(PenflowApprovalError, match="semantics_changed"):
        package_review_result(project.root, Path(snapshot["snapshot"]["path"]), output)
    assert not project.baseline.exists()


def test_blocking_review_is_preserved_but_cannot_approve(project: ReviewProject) -> None:
    snapshot = project.snapshot()
    output = _output(project, snapshot)
    value = _read_json(output)
    value.update(
        {
            "verdict": "BLOCKING",
            "blocking_count": 1,
            "findings": [
                {
                    "severity": "BLOCKING",
                    "message": "Outcome needs correction",
                    "requirement_ids": [f"livespec:{FEATURE}:FR-001"],
                }
            ],
        }
    )
    _write_json(output, value)
    result = package_review_result(project.root, Path(snapshot["snapshot"]["path"]), output)
    assert result["verdict"] == "BLOCKING" and result["certified"] is False
    with pytest.raises(PenflowApprovalError, match="not_approved"):
        project.approve(project.root / result["result"]["path"])
    assert not project.baseline.exists()


@pytest.mark.parametrize("severity", ["WARNING", "BLOCKING"])
def test_retirement_findings_can_reference_authenticated_old_ids(
    project: ReviewProject, severity: str
) -> None:
    project.approve(project.result(project.snapshot()))
    project.complete_review()
    project.spec.write_text(project.spec.read_text().replace("visual: true", "visual: false"))
    snapshot = project.snapshot()
    output = _output(project, snapshot)
    value = _read_json(output)
    value.update(
        {
            "verdict": "PASS" if severity == "WARNING" else "BLOCKING",
            "blocking_count": int(severity == "BLOCKING"),
            "findings": [
                {
                    "severity": severity,
                    "message": "Review removed behavior",
                    "requirement_ids": [f"livespec:{FEATURE}:FR-001"],
                }
            ],
        }
    )
    _write_json(output, value)
    result = package_review_result(project.root, Path(snapshot["snapshot"]["path"]), output)
    if severity == "BLOCKING":
        with pytest.raises(PenflowApprovalError, match="not_approved"):
            project.approve(project.root / result["result"]["path"])
    else:
        baseline = project.approve(project.root / result["result"]["path"])
        assert baseline["projection"]["requirements"] == []
        require_approved_requirements(project.root, FEATURE, disposition="retired")
