"""Independent closure distinguishes terminal progression from CLI usage errors."""

# @spec FR-009: Preserve reviewed coordinator identity
# .specs/features/078-requirement-evidence-integrity/spec.md#fr-009
# @spec AC-015: Reject unproven successful coordinator closure
# .specs/features/078-requirement-evidence-integrity/spec.md#ac-015

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from tests.integration.helpers import witness_pipeline as pipeline
from tests.integration.helpers.witness_process import ProcessCapture
from tests.review_support import reviewed_project
from tests.test_pipeline import PIPELINE_MD
from validator.cli import app


@pytest.mark.parametrize("phase_state", ["complete", "pending", "usage_error"])
def test_terminal_probe_uses_review_identity_and_rejects_usage_exit_two(
    tmp_path, monkeypatch, phase_state
):
    feature = reviewed_project(tmp_path)
    content = PIPELINE_MD.replace("Pending", "Done")
    if phase_state == "pending":
        content = PIPELINE_MD
    (feature / "pipeline.md").write_text(content)
    monkeypatch.chdir(tmp_path)

    def invoke_actual_cli(argv, cwd, timeout, *, env):
        args = argv[1:]
        if phase_state == "usage_error":
            args.remove("--feature")  # Reproduce the observed real Typer error.
        result = CliRunner().invoke(app, args)
        return ProcessCapture(result.exit_code, result.stdout, result.stderr, 0)

    monkeypatch.setattr(pipeline, "run_process", invoke_actual_cli)
    accepted = pipeline._terminal_pipeline(
        "livespec", tmp_path, "001-test", {}, {"flags": ["--model=reviewer/v1"]}
    )
    assert accepted is (phase_state == "complete")


def test_terminal_probe_rejects_incomplete_process_control(tmp_path, monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "run_process",
        lambda *args, **kwargs: ProcessCapture(2, "", "", 0, control_complete=False),
    )
    assert not pipeline._terminal_pipeline("livespec", tmp_path, "001-test", {}, {})
