"""Real file-bound approval lifecycle; reviewer outputs are protocol fixtures, not LLM reviews."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from tests.penflow_approval_fixtures import canonical_approval_contract, configure_protocol_policy
from validator import penflow_review_approval as approval_engine
from validator.locks import acquire_lock
from validator.penflow_approval_files import PenflowApprovalError, archive_json
from validator.penflow_review_approval import approve_review_result, require_approved_requirements
from validator.penflow_review_snapshot import create_review_snapshot

# @spec AC-008: Reviewed source lifecycle and failure boundaries
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#ac-008

FEATURE = "001-save-profile"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True))


def _reference(root: Path, path: Path) -> dict[str, str]:
    return {
        "path": str(path.relative_to(root)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


@dataclass
class ReviewProject:
    root: Path
    spec: Path
    plan: Path
    contract: Path

    @property
    def baseline(self) -> Path:
        return self.root / ".specs/penflow-requirements.json"

    def snapshot(self) -> dict[str, Any]:
        return create_review_snapshot(self.root, FEATURE)

    def result(self, snapshot: dict[str, Any]) -> Path:
        """Produce exact fixture review bytes and an independently hashed wrapper."""
        identity = snapshot["input_sha256"]
        output = self.root / f"review-output-{identity}.json"
        review = {
            "invocation_id": f"protocol-fixture-{identity}",
            "producer_id": "test-only-reviewer",
            "input_sha256": identity,
            "verdict": "PASS",
            "blocking_count": 0,
            "findings": [],
        }
        _write_json(output, review)
        result = self.root / f"review-result-{identity}.json"
        _write_json(
            result,
            {
                "kind": "livespec-penflow-review-result",
                "version": 1,
                "snapshot": snapshot["snapshot"],
                "review": {**review, "output": _reference(self.root, output)},
            },
        )
        return result

    def approve(self, result: Path) -> dict[str, Any]:
        with acquire_lock(self.root / ".specs"):
            return approve_review_result(self.root, FEATURE, result)

    def complete_review(self) -> None:
        (self.spec.parent / "pipeline.md").write_text(
            "| Phase | Status |\n| Plan Review | Done |\n"
        )


@pytest.fixture
def project(tmp_path: Path) -> ReviewProject:
    feature = tmp_path / ".specs/features" / FEATURE
    feature.mkdir(parents=True)
    spec = feature / "spec.md"
    spec.write_text(
        "---\nstatus: Approved\nupdated: 2026-09-05\nvisual: true\n---\n# Save profile\n\n"
        "## Functional Requirements\n\n"
        "- **FR-001:** Save the display name (AC-001).\n"
        "- **FR-002:** Persist the saved name (AC-002).\n\n"
        "## Acceptance Criteria\n\n"
        "- **AC-001:** Show the new name after save.\n"
        "- **AC-002:** Retain the name after reopening.\n"
    )
    plan = feature / "plan.md"
    plan.write_text("---\nstatus: Approved\n---\n# Plan\n\nUse the profile storage adapter.\n")
    configure_protocol_policy(tmp_path)
    contract = tmp_path / "penflow/flow-ui-contract/contract.json"
    _write_json(
        contract,
        canonical_approval_contract(
            [_reference(tmp_path, spec)],
            [
                {"requirement_id": f"livespec:{FEATURE}:{identifier}", "obligation_id": "save"}
                for identifier in ["FR-001", "FR-002", "AC-001", "AC-002"]
            ],
            ["save"],
        ),
    )
    return ReviewProject(tmp_path, spec, plan, contract)


def _approved(project: ReviewProject) -> dict[str, Any]:
    baseline = project.approve(project.result(project.snapshot()))
    project.complete_review()
    return baseline


def test_exact_snapshot_review_and_replay_publish_one_authority(project: ReviewProject) -> None:
    snapshot = project.snapshot()
    result = project.result(snapshot)
    baseline = project.approve(result)
    assert _read_json(project.baseline) == baseline
    assert baseline["disposition"] == "active"
    assert baseline["selection"] == [FEATURE]
    assert len(baseline["projection"]["requirements"]) == 4
    assert baseline["projection"]["uncovered"] == []
    (project.spec.parent / "pipeline.md").write_text("| Plan Review | Pending |\n")
    with pytest.raises(PenflowApprovalError, match="plan_review_not_completed"):
        require_approved_requirements(project.root, FEATURE)
    project.complete_review()
    require_approved_requirements(project.root, FEATURE)
    archived = sorted((project.root / ".specs/penflow-approvals").iterdir())
    assert project.approve(result) == baseline
    assert sorted((project.root / ".specs/penflow-approvals").iterdir()) == archived


def test_history_rechecks_immutable_bytes_on_every_invocation(project: ReviewProject) -> None:
    baseline = _approved(project)
    require_approved_requirements(project.root, FEATURE)
    archived = project.root / baseline["sources"][0]["reviewed_snapshot"]["path"]
    archived.write_bytes(archived.read_bytes() + b"\nAltered business requirement\n")
    with pytest.raises(PenflowApprovalError, match="approval_reference_stale"):
        require_approved_requirements(project.root, FEATURE)


def test_shared_archive_cannot_satisfy_another_expected_raw_hash(project: ReviewProject) -> None:
    project.plan.write_bytes(project.spec.read_bytes())
    baseline = _approved(project)
    approval = _read_json(project.root / baseline["approval_receipts"][0]["path"])
    snapshot = _read_json(project.root / approval["snapshot"]["path"])
    assert (
        snapshot["inputs"]["sources"][0]["reviewed_snapshot"]
        == snapshot["inputs"]["plans"][0]["reviewed_snapshot"]
    )
    snapshot["inputs"]["plans"][0]["sha256"] = "f" * 64
    # This adversarial protocol fixture binds every outer reference correctly,
    # isolating the incompatible expected raw hash for the shared source archive.
    with acquire_lock(project.root / ".specs"):
        reference = archive_json(project.root, snapshot, prefix="snapshot")
        review = {key: value for key, value in approval["review"].items() if key != "output"}
        review["input_sha256"] = reference["sha256"]
        output = archive_json(project.root, review, prefix="review-output")
        approval.update(
            {
                "snapshot": reference,
                "inputs": snapshot["inputs"],
                "review": {**review, "output": output},
            }
        )
        baseline["approval_receipts"] = [archive_json(project.root, approval, prefix="approval")]
    with pytest.raises(PenflowApprovalError, match="historical_source_snapshot_mismatch"):
        approval_engine.validate_approval_history(project.root, baseline)


@pytest.mark.parametrize("target", ["spec", "plan"])
def test_changed_review_inputs_cannot_publish(project: ReviewProject, target: str) -> None:
    result = project.result(project.snapshot())
    path = getattr(project, target)
    path.write_text(path.read_text() + "\nChanged business behavior.\n")
    with pytest.raises(PenflowApprovalError, match="semantics_changed"):
        project.approve(result)
    assert not project.baseline.exists()


def test_only_lifecycle_metadata_can_change_after_approval(project: ReviewProject) -> None:
    _approved(project)
    project.spec.write_text(
        project.spec.read_text()
        .replace("status: Approved", "status: Implemented")
        .replace("2026-09-05", "2026-09-06")
    )
    require_approved_requirements(project.root, FEATURE)
    project.spec.write_text(project.spec.read_text().replace("visual: true", "visual: false"))
    with pytest.raises(PenflowApprovalError, match="semantics_changed"):
        require_approved_requirements(project.root, FEATURE)


@pytest.mark.parametrize("change", ["category", "predicate"])
def test_changed_outcome_mapping_blocks_current_approval(
    project: ReviewProject, change: str
) -> None:
    _approved(project)
    contract = _read_json(project.contract)
    outcome = contract["outcome_expectations"][0]
    if change == "category":
        outcome["category"] = "action"
    else:
        outcome["assertions"][0]["expected"] = "Grace"
    _write_json(project.contract, contract)
    with pytest.raises(PenflowApprovalError, match="contract_changed"):
        require_approved_requirements(project.root, FEATURE)


def test_baseline_deletion_does_not_reset_adopted_authority(project: ReviewProject) -> None:
    _approved(project)
    project.baseline.unlink()
    with pytest.raises(PenflowApprovalError, match="accepted_baseline_removed"):
        project.snapshot()


def test_reviewed_reduction_retains_previous_approval(project: ReviewProject) -> None:
    old = _approved(project)
    old_bytes = project.baseline.read_bytes()
    project.spec.write_text(
        "\n".join(
            line
            for line in project.spec.read_text().splitlines()
            if "**FR-002:**" not in line and "**AC-002:**" not in line
        )
        + "\n"
    )
    contract = _read_json(project.contract)
    contract["requirements"]["source_refs"] = [_reference(project.root, project.spec)]
    contract["requirements"]["bindings"] = [
        row
        for row in contract["requirements"]["bindings"]
        if not row["requirement_id"].endswith(("FR-002", "AC-002"))
    ]
    _write_json(project.contract, contract)
    snapshot = project.snapshot()
    reviewed = _read_json(project.root / snapshot["snapshot"]["path"])
    assert set(reviewed["changes"][0]["removed_requirement_ids"]) == {
        f"livespec:{FEATURE}:FR-002",
        f"livespec:{FEATURE}:AC-002",
    }
    assert (project.root / reviewed["prior_receipt"]["path"]).read_bytes() == old_bytes
    new = project.approve(project.result(snapshot))
    assert new["previous"] == reviewed["prior_receipt"]
    assert new["approval_receipts"] != old["approval_receipts"]
    assert len(new["projection"]["requirements"]) == 2
    require_approved_requirements(project.root, FEATURE)


def test_unselected_backlog_is_ignored_but_caller_selection_is_enforced(
    project: ReviewProject,
) -> None:
    backlog = project.root / ".specs/features/999-backlog"
    backlog.mkdir()
    (backlog / "spec.md").write_bytes(b"\xff invalid unrelated spec")
    _approved(project)
    require_approved_requirements(project.root, FEATURE)
    with pytest.raises(PenflowApprovalError, match="selection_or_scope_mismatch"):
        require_approved_requirements(project.root, "999-backlog")


def test_wrapper_pass_cannot_override_actual_blocking_review(project: ReviewProject) -> None:
    result_path = project.result(project.snapshot())
    result = _read_json(result_path)
    output_path = project.root / result["review"]["output"]["path"]
    output = _read_json(output_path)
    output.update(verdict="BLOCKING", blocking_count=1)
    _write_json(output_path, output)
    result["review"]["output"] = _reference(project.root, output_path)
    _write_json(result_path, result)
    with pytest.raises(PenflowApprovalError, match="review_output_not_approved"):
        project.approve(result_path)
    assert not project.baseline.exists()


def test_mutated_immutable_review_source_blocks_reclosure(project: ReviewProject) -> None:
    baseline = _approved(project)
    archived = project.root / baseline["sources"][0]["reviewed_snapshot"]["path"]
    archived.write_text(archived.read_text() + "\nTampered history.\n")
    with pytest.raises(PenflowApprovalError, match="reference_stale"):
        require_approved_requirements(project.root, FEATURE)


def test_review_result_cannot_name_a_different_input_digest(project: ReviewProject) -> None:
    result_path = project.result(project.snapshot())
    result = _read_json(result_path)
    result["review"]["input_sha256"] = "0" * 64
    _write_json(result_path, result)
    with pytest.raises(PenflowApprovalError, match="review_input_identity_mismatch"):
        project.approve(result_path)
    assert not project.baseline.exists()


@pytest.mark.parametrize("severity,requirement", [("BLOCKING", "FR-001"), ("INFO", "FR-999")])
def test_review_findings_are_checked_beyond_pass_label(
    project: ReviewProject, severity: str, requirement: str
) -> None:
    result_path = project.result(project.snapshot())
    result = _read_json(result_path)
    output_path = project.root / result["review"]["output"]["path"]
    output = _read_json(output_path)
    findings = [
        {
            "severity": severity,
            "message": "Protocol fixture finding",
            "requirement_ids": [f"livespec:{FEATURE}:{requirement}"],
        }
    ]
    output["findings"] = findings
    _write_json(output_path, output)
    result["review"]["findings"] = findings
    result["review"]["output"] = _reference(project.root, output_path)
    _write_json(result_path, result)
    with pytest.raises(
        PenflowApprovalError, match=r"review_blocking_findings|unknown_requirements"
    ):
        project.approve(result_path)
    assert not project.baseline.exists()


def test_interrupted_baseline_publication_can_retry_same_review(
    project: ReviewProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = project.result(project.snapshot())
    original = approval_engine.write_with_hash_check

    def interrupt(path: Path, content: str, *args: Any, **kwargs: Any) -> Any:
        if path == project.baseline:
            raise OSError("Injected interruption before authority publication")
        return original(path, content, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(approval_engine, "write_with_hash_check", interrupt)
        with pytest.raises(OSError, match="Injected interruption"):
            project.approve(result)
    assert not project.baseline.exists()
    project.approve(result)
    project.complete_review()
    require_approved_requirements(project.root, FEATURE)
