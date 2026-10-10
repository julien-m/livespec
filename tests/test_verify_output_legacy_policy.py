"""Archive policy spelling never upgrades historical runner evidence at the CLI boundary."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.execution_evidence_support import AC, FEATURE
from tests.execution_evidence_support import project as project
from tests.test_execution_capture_policy import _historical_run
from tests.test_verify_output_cli import write_artifact
from validator.cli import app
from validator.execution_evidence import verify_execution_receipt


@pytest.mark.parametrize("policy", [None, "legacy", "1", "2", "future"])
def test_cli_rechecks_old_capture_under_original_archive_policy(project, monkeypatch, policy):
    monkeypatch.chdir(project)
    receipt = _historical_run(project, monkeypatch, None)
    assert verify_execution_receipt(receipt, project, FEATURE, (AC,), evidence_policy="1").valid
    path = write_artifact(project / ".specs/.runs")
    artifact = json.loads(path.read_text())
    artifact["feature"] = FEATURE
    artifact["receipts"] = [{"kind": "execution", "path": str(receipt)}]
    if policy is not None:
        artifact["evidence_policy_version"] = policy
    path.write_text(json.dumps(artifact))
    result = CliRunner().invoke(app, ["verify-output", "spec-specify", "--run", str(path)])
    assert (result.exit_code == 0) is (policy in (None, "legacy", "1")), result.output
    assert Path(receipt).is_file()
