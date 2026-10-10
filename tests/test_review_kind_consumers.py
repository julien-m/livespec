"""Review obligations select their canonical purpose rather than the supplied receipt."""

from pathlib import Path

import pytest

from tests.review_support import reviewed_project
from validator.evidence_policy import typed_evidence_missing
from validator.run_receipts import verify_evidence_receipts


@pytest.mark.parametrize("expected,supplied", [("spec", "plan"), ("plan", "spec")])
def test_typed_goal_and_archive_reject_the_wrong_review_kind(tmp_path: Path, expected, supplied):
    directory = reviewed_project(tmp_path)
    evidence = {"review_receipt_path": str(directory / f".reviews/{supplied}.json")}
    task = {
        "evidence_kind": "review",
        "expected_evidence": {"review_kind": expected, "reviewer_model": "reviewer/v1"},
        "accepted_evidence": evidence,
    }
    missing = typed_evidence_missing(
        task,
        evidence,
        contract={"feature": directory.name, "evidence_policy_version": "2"},
        project_root=tmp_path,
    )
    assert missing
    checked = verify_evidence_receipts(
        [task], project_root=tmp_path, feature=directory.name, reviewer_model="reviewer/v1"
    )
    assert len(checked) == 1 and not checked[0].verified
