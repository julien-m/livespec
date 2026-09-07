"""Changed snapshot inputs remain explicit invalid trials with persisted reports."""

# @spec(FR-014)

from __future__ import annotations

import json

import pytest

from tests.integration.helpers import witness_pipeline as pipeline
from tests.integration.helpers.witness_snapshot import workflow_identity


@pytest.mark.parametrize("change", ["deleted", "symlink", "changed"])
def test_trial_publishes_invalid_report_for_changed_catalog_dependency(
    tmp_path, monkeypatch, change
):
    snapshot = tmp_path / "workflow"
    catalog = snapshot / "validator/conventions_ast/rule_catalog/minimal.yaml"
    catalog.parent.mkdir(parents=True)
    catalog.write_text(
        "rules:\n- fixtures: {pass: pass.py, fail: fail.py}\n"
        "  deterministic_test_evidence:\n"
        "  - {test: test.py, pass_fixture: pass.py, fail_fixture: fail.py}\n"
    )
    for name in (
        "VERSION",
        "pyproject.toml",
        ".specs/spec-system.md",
        "pass.py",
        "fail.py",
        "test.py",
    ):
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("original")
    identity = workflow_identity(snapshot)
    dependency = snapshot / "test.py"
    if change == "changed":
        dependency.write_text("changed")
    else:
        dependency.unlink()
        if change == "symlink":
            dependency.symlink_to(snapshot / "pass.py")

    def finalize_trial(result, oracle, executable, timeout, budget, payload):
        # Replace external generation only; actual finalization and report writing remain real.
        pipeline._finish(result, identity, snapshot, True)

    monkeypatch.setattr(pipeline, "_run_pipeline_workspace", finalize_trial)
    report = tmp_path / "trial.json"
    result = pipeline.run_pipeline_trial("echo", report_path=report)
    assert result.outcome == "invalid"
    persisted = json.loads(report.read_text())
    assert persisted["outcome"] == "invalid"
    assert persisted["reason"].startswith("production_workflow_")
