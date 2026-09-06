"""Use the real Penflow subprocess for the C20 guard; no runtime certificate is implied."""

import json

import pytest

from tests.test_penflow_review_approval import ReviewProject
from tests.test_penflow_review_approval import project as project
from validator.penflow_approval_files import PenflowApprovalError
from validator.penflow_contract_validation import validate_review_contract


def test_real_c20_guard_is_readonly(project: ReviewProject) -> None:
    before = project.contract.read_bytes()
    validate_review_contract(project.root, project.contract)
    assert project.contract.read_bytes() == before


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "invalid-schema"])
def test_real_c20_guard_rejects_unreviewable_contract(
    project: ReviewProject, mutation: str
) -> None:
    contract = json.loads(project.contract.read_text())
    if mutation == "missing":
        contract["nodes"][0].pop("test_id")
    elif mutation == "duplicate":
        contract["nodes"][1]["test_id"] = contract["nodes"][0]["test_id"]
    else:
        contract["version"] = 999
    project.contract.write_text(json.dumps(contract))
    before = project.contract.read_bytes()
    with pytest.raises(PenflowApprovalError, match="review_contract_validation_failed"):
        validate_review_contract(project.root, project.contract)
    assert project.contract.read_bytes() == before


def test_absent_penflow_cannot_approve_contract(
    project: ReviewProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", "")
    with pytest.raises(PenflowApprovalError, match="review_contract_penflow_cli_required"):
        validate_review_contract(project.root, project.contract)
