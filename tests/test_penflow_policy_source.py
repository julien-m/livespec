"""Workflow policy tests use explicit protocol fixtures, never native certification."""

import json
from pathlib import Path

import pytest
import yaml

from tests.penflow_approval_fixtures import protocol_policy_decisions
from tests.test_penflow_approval_multifeature import (
    SECOND,
    _add_second,
    _approve_protocol_fixture,
    _canonical_contract_fixture,
    _feature_file,
)
from tests.test_penflow_review_approval import FEATURE, ReviewProject
from tests.test_penflow_review_approval import project as project
from validator.penflow_approval_files import (
    PenflowApprovalError,
    archive_bytes,
    archive_json,
    load_object,
    read_ref,
)
from validator.penflow_policy_source import (
    POLICY_SOURCE,
    has_workflow_policy,
    validate_policy_reference,
    workflow_decisions,
)
from validator.penflow_review_approval import require_approved_requirements
from validator.penflow_review_snapshot import create_review_snapshot


@pytest.mark.parametrize(
    "metadata",
    [
        "{}",
        "{unknown: {}}",
        "{livespec: {version: true}}",
        "{livespec: {}, livespec: {}}",
        "{livespec: {version: 1, generated_docs: required, generated_docs: not_applicable, "
        "native_geometry: required, homologous_references: not_applicable, "
        "native_export: not_applicable}}",
    ],
)
def test_workflow_metadata_is_closed_and_unambiguous(metadata: str) -> None:
    with pytest.raises(ValueError):
        workflow_decisions(
            f"---\npenflow_verification_policy: {metadata}\n---\nActual workflow".encode(),
            inherited=False,
        )


def test_new_snapshot_requires_actual_policy_source(project: ReviewProject) -> None:
    root, feature = project.root, FEATURE
    (root / POLICY_SOURCE).unlink()
    with pytest.raises(PenflowApprovalError, match="verification_policy_source_required"):
        create_review_snapshot(root, feature)


def test_policy_is_not_copied_from_candidate_c20(project: ReviewProject) -> None:
    root, feature = project.root, FEATURE
    path = root / "penflow/flow-ui-contract/contract.json"
    contract = json.loads(path.read_text())
    contract["verification_policy"]["native_geometry"] = "not_applicable"
    path.write_text(json.dumps(contract))
    with pytest.raises(PenflowApprovalError, match="reviewed_verification_policy_mismatch"):
        create_review_snapshot(root, feature)


def test_archived_workflow_is_required_after_generation(project: ReviewProject) -> None:
    root, feature = project.root, FEATURE
    source = load_object((root / POLICY_SOURCE).read_bytes())
    (root / source["workflow"]["path"]).write_text("changed workflow")
    with pytest.raises(PenflowApprovalError, match="approval_reference_stale"):
        create_review_snapshot(root, feature)


def test_current_source_cannot_differ_from_reviewed_archive(project: ReviewProject) -> None:
    root = project.root
    source = load_object((root / POLICY_SOURCE).read_bytes())
    reference = archive_json(root, source, prefix="verification-policy")
    (root / POLICY_SOURCE).write_text(json.dumps(source, indent=4))
    contract = json.loads((root / "penflow/flow-ui-contract/contract.json").read_text())
    with pytest.raises(PenflowApprovalError, match="verification_policy_source_changed"):
        validate_policy_reference(root, reference, contract, current=True)


def _plan_policy(path: Path, *, required: bool) -> None:
    decisions = protocol_policy_decisions()
    if not required:
        decisions = {key: "not_applicable" for key in decisions if key != "version"}
        decisions["version"] = 1
    path.write_text(
        "---\n"
        + yaml.safe_dump({"penflow_verification_policy": {"livespec": decisions}})
        + "---\n# Actual protocol fixture plan\n\nExecute the declared procedures.\n"
    )


def test_active_plan_union_survives_second_feature_and_allows_governed_retirement(
    project: ReviewProject,
) -> None:
    _plan_policy(project.plan, required=True)
    _canonical_contract_fixture(project, [FEATURE])
    _approve_protocol_fixture(project, FEATURE)
    _add_second(project)
    _plan_policy(_feature_file(project, SECOND, "plan.md"), required=False)
    _canonical_contract_fixture(project, [FEATURE, SECOND])
    _approve_protocol_fixture(project, SECOND)
    for name in [FEATURE, SECOND]:
        require_approved_requirements(project.root, name)
    source = load_object((project.root / POLICY_SOURCE).read_bytes())
    assert source["decisions"] == protocol_policy_decisions()

    project.spec.write_text(project.spec.read_text().replace("visual: true", "visual: false"))
    _canonical_contract_fixture(project, [SECOND])
    contract = json.loads(project.contract.read_text())
    contract["verification_policy"] = {
        key: "not_applicable" for key in protocol_policy_decisions() if key != "version"
    }
    contract["verification_policy"]["version"] = 1
    project.contract.write_text(json.dumps(contract))
    # The old approval cannot certify a policy reduction before the new review.
    with pytest.raises(PenflowApprovalError):
        require_approved_requirements(project.root, SECOND)
    _approve_protocol_fixture(project, FEATURE)
    require_approved_requirements(project.root, SECOND)
    source = load_object((project.root / POLICY_SOURCE).read_bytes())
    assert source["decisions"] == contract["verification_policy"]


def test_latest_plan_cannot_omit_earlier_active_plan_policy(project: ReviewProject) -> None:
    _plan_policy(project.plan, required=True)
    _canonical_contract_fixture(project, [FEATURE])
    _approve_protocol_fixture(project, FEATURE)
    _add_second(project)
    _canonical_contract_fixture(project, [FEATURE, SECOND])
    previous = project.baseline.read_bytes()
    with pytest.raises(PenflowApprovalError, match="required_in_every_active_plan"):
        create_review_snapshot(project.root, SECOND)
    assert project.baseline.read_bytes() == previous


def test_plan_policy_examples_do_not_become_authority() -> None:
    assert not has_workflow_policy(b"# Plan\n```yaml\npenflow_verification_policy: {}\n```\n")
    with pytest.raises(PenflowApprovalError, match="duplicate_or_invalid_key"):
        has_workflow_policy(b"---\nstatus: Approved\nstatus: Draft\n---\n# Plan")


def test_plan_policy_frontmatter_matches_core_delimiter_semantics() -> None:
    declared = protocol_policy_decisions()
    raw = (
        "----\n"
        + yaml.safe_dump({"penflow_verification_policy": {"livespec": declared}})
        + "-----\n# Actual protocol workflow\n"
    ).encode()
    assert workflow_decisions(raw, inherited=False) == declared


def test_validation_recomputes_plan_union_instead_of_trusting_generated_policy(
    project: ReviewProject,
) -> None:
    _plan_policy(project.plan, required=True)
    result = create_review_snapshot(project.root, FEATURE)
    snapshot = load_object(read_ref(project.root, result["snapshot"]))
    source = load_object((project.root / POLICY_SOURCE).read_bytes())
    weaker = {**source["decisions"], "native_geometry": "not_applicable"}
    source["decisions"] = weaker
    workflow = (
        "---\n"
        + yaml.safe_dump({"penflow_verification_policy": {"livespec": weaker}})
        + "---\n# Candidate weaker workflow\n"
    ).encode()
    source["workflow"] = archive_bytes(project.root, workflow, prefix="workflow", suffix=".md")
    reference = archive_json(project.root, source, prefix="verification-policy")
    contract = json.loads(project.contract.read_text())
    contract["verification_policy"] = weaker
    with pytest.raises(PenflowApprovalError, match="active_plan_verification_policy_mismatch"):
        validate_policy_reference(
            project.root, reference, contract, plans=snapshot["inputs"]["plans"], active=[FEATURE]
        )
