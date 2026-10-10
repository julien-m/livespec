"""Historical artifacts stay readable without certifying new execution claims."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.test_goal_archive_cli import write_pair
from tests.test_review_context import prepare, response
from validator.cli import app
from validator.evidence_policy import EVIDENCE_POLICY_VERSION, typed_evidence_missing
from validator.run_artifacts import load_run_artifact
from validator.semantic import review_context
from validator.semantic.review_contract import validate_review_result
from validator.semantic.review_receipts import save_review_receipt, verify_review_receipt


@pytest.mark.parametrize("field", ["POLICY_VERSION", "SCHEMA_VERSION", "PROMPT_VERSION"])
def test_current_policy_schema_or_prompt_change_rejects_old_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    prepared = prepare()
    receipt = validate_review_result(prepared, [json.dumps(response(prepared))])
    path = save_review_receipt(tmp_path / "review.json", receipt)
    assert receipt.ready and verify_review_receipt(path, prepared)
    monkeypatch.setattr(review_context, field, "next-version")
    current = prepare()
    assert current.context_hash != prepared.context_hash
    assert not verify_review_receipt(path, current)


def test_legacy_archive_remains_readable_but_cannot_certify_current_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".specs").mkdir()
    monkeypatch.chdir(tmp_path)
    contract, state = write_pair(tmp_path)
    runner = CliRunner()
    archived = runner.invoke(
        app,
        [
            "goal",
            "archive",
            "--contract",
            str(contract),
            "--state",
            str(state),
            "--exit-code",
            "0",
            "--json",
        ],
    )
    assert archived.exit_code == 0, archived.output
    path = Path(json.loads(archived.output)["archived"])
    historical = load_run_artifact(path)
    assert historical["evidence_policy_version"] == "legacy"
    reread = runner.invoke(app, ["verify-output", "spec-specify", "--run", str(path)])
    assert reread.exit_code == 0, reread.output
    missing = typed_evidence_missing(
        {"evidence_kind": "execution"},
        {"execution_receipt_path": str(path)},
        contract={"evidence_policy_version": EVIDENCE_POLICY_VERSION, "feature": "001-test"},
        project_root=tmp_path,
    )
    assert missing, "A readable historical archive must not stand in for a runner capture"
