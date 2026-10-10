"""Current archive reads retain immutable documentary and execution obligations."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.execution_evidence_support import project as project
from tests.test_acceptance_execution_join import _archive, _complete_goal, _joined_goal
from validator.cli import app


@pytest.mark.parametrize(
    "mutation",
    ["receipts", "state", "contract", "policy", "inventory", "command", "downgrade", "alias"],
)
def test_current_archive_cannot_erase_acceptance_obligations(project, monkeypatch, mutation):
    contract, state, evidence = _joined_goal(project)
    state = _complete_goal(contract, state, evidence, project)
    archived = _archive(project, contract, state, monkeypatch)
    assert archived.exit_code == 0, archived.output
    path = Path(json.loads(archived.output)["archived"])
    artifact = json.loads(path.read_text())
    if mutation in {"downgrade", "alias"}:
        artifact.pop("evidence_contract")
        artifact["evidence_policy_version"] = "1"
        artifact["receipts"] = []
        Path(evidence["acceptance_review_receipt_path"]).write_text('{"reviewed":true}')
    elif mutation == "receipts":
        artifact["receipts"] = []
        Path(evidence["acceptance_review_receipt_path"]).write_text('{"reviewed":true}')
    elif mutation == "state":
        artifact["goal"]["tasks"] = []
    elif mutation == "contract":
        artifact.pop("evidence_contract")
    elif mutation == "policy":
        artifact["evidence_policy_version"] = "1"
    elif mutation == "command":
        artifact["command"] = "spec-other"
        artifact["evidence_contract"]["command"] = "spec-other"
    else:
        task = next(
            item
            for item in artifact["evidence_contract"]["tasks"]
            if item.get("acceptance_scope") == "feature"
        )
        task["expected_evidence"]["acceptance_inventory"] = []
    path.write_text(json.dumps(artifact))
    if mutation == "alias":
        alias = path.with_name("legacy-alias.json")
        alias.symlink_to(path)
        path = alias
    result = CliRunner().invoke(app, ["verify-output", "spec-demo", "--run", str(path)])
    assert result.exit_code != 0, result.output


def test_policy_suffix_preserves_command_lookup_and_timestamp_order(tmp_path):
    from validator.run_artifacts import find_latest_artifact

    old = tmp_path / "spec-demo-2026-06-10T10-00-00-aaaaaaaa.json"
    current = tmp_path / "spec-demo-2026-06-10T11-00-00-bbbbbbbb-policy2.json"
    other = tmp_path / "spec-other-2026-06-10T12-00-00-cccccccc-policy2.json"
    for path in (old, current, other):
        path.write_text("{}")
    assert find_latest_artifact("spec-demo", tmp_path) == current
    later_legacy = tmp_path / "spec-demo-2026-06-10T13-00-00-dddddddd.json"
    later_legacy.write_text("{}")
    assert find_latest_artifact("spec-demo", tmp_path) == later_legacy
