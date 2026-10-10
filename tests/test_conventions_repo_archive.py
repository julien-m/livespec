"""Archive convention scopes retain distinct identities and legacy skip behavior."""

from pathlib import Path

import pytest

from tests.test_conventions_final_evidence import FEATURE, _final_fixture
from validator.run_receipts import verify_evidence_receipts, verify_one_receipt
from validator.verify_output import _evaluate_receipt_verdict


def test_ac001_archive_collects_distinct_feature_and_repo_kinds(tmp_path: Path) -> None:
    project, _, _, _, evidence = _final_fixture(tmp_path)
    checks = verify_evidence_receipts(
        [{"accepted_evidence": evidence}], project_root=project, feature=FEATURE
    )
    assert {check.kind for check in checks} == {"conventions", "conventions_repo"}
    assert all(check.verified and check.verdict == "PASS" for check in checks)


def test_ac007_archive_repo_kind_rejects_feature_identity(tmp_path: Path) -> None:
    project, _, _, _, evidence = _final_fixture(tmp_path)
    path = evidence["conventions_receipt_path"]
    assert isinstance(path, str)
    check = verify_one_receipt(
        kind="conventions_repo", path=path, project_root=project, feature=FEATURE
    )
    assert check.verified is False
    assert check.error == "feature_slug_mismatch"


@pytest.mark.parametrize("kind", ["conventions", "conventions_repo"])
def test_ac003_unmigrated_gates_absent_skips_both_kinds(tmp_path: Path, kind: str) -> None:
    result = _evaluate_receipt_verdict("MUST", {"kind": kind, "verdict": "PASS"}, {}, tmp_path)
    assert result.status == "SKIP"


@pytest.mark.parametrize("verdict", ["PASS", "FAIL", "BLOCKED"])
def test_ac003_migrated_repo_rule_requires_matching_pass(tmp_path: Path, verdict: str) -> None:
    (tmp_path / ".specs").mkdir()
    (tmp_path / ".specs/conventions-gates.yaml").write_text("schema_version: 1\n")
    artifact = {"receipts": [{"kind": "conventions_repo", "verified": True, "verdict": verdict}]}
    result = _evaluate_receipt_verdict(
        "MUST", {"kind": "conventions_repo", "verdict": "PASS"}, artifact, tmp_path
    )
    assert result.status == ("PASS" if verdict == "PASS" else "FAIL")


def test_ac003_feature_kind_cannot_satisfy_repo_archive_rule(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir()
    (tmp_path / ".specs/conventions-gates.yaml").write_text("schema_version: 1\n")
    artifact = {"receipts": [{"kind": "conventions", "verified": True, "verdict": "PASS"}]}
    result = _evaluate_receipt_verdict(
        "MUST", {"kind": "conventions_repo", "verdict": "PASS"}, artifact, tmp_path
    )
    assert result.status == "FAIL"
