# @spec(AC-011)
# .specs/features/078-requirement-evidence-integrity/spec.md#ac-011
"""Prepared-source generation never imports authority by copying or trusts model exit alone."""

from pathlib import Path

from tests.integration.helpers import witness_generation, witness_prepared_ui
from tests.integration.helpers.witness_generation import run_generation_trial
from tests.integration.helpers.witness_process import ProcessCapture


def test_uncertified_source_preserves_existing_index(tmp_path, monkeypatch):
    candidate = tmp_path / "consumer"
    candidate.mkdir()
    (candidate / "index.html").write_text("previous")
    monkeypatch.setattr(witness_prepared_ui.shutil, "which", lambda _: "codex")
    monkeypatch.setattr(witness_prepared_ui, "_penflow_executable", lambda: "penflow")
    monkeypatch.setattr(witness_prepared_ui, "_design_authority", lambda *args: False)
    result = run_generation_trial(
        "ui-form", "codex", prepared_ui_candidate=candidate, report_path=tmp_path / "report.json"
    )
    assert result.outcome == "evidence_incomplete" and result.attempts == 0
    assert (candidate / "index.html").read_text() == "previous"


def test_prepared_source_rejects_model_mutation_before_evaluation(tmp_path, monkeypatch):
    candidate = tmp_path / "consumer"
    candidate.mkdir()
    for name in witness_prepared_ui.NORMATIVE:
        path = candidate / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("frozen")
    (candidate / "index.html").write_text("previous")
    monkeypatch.setattr(witness_prepared_ui.shutil, "which", lambda _: "codex")
    monkeypatch.setattr(witness_prepared_ui, "_penflow_executable", lambda: "penflow")
    monkeypatch.setattr(witness_prepared_ui, "_design_authority", lambda *args: True)
    monkeypatch.setattr(
        witness_prepared_ui, "run_process", lambda *a: ProcessCapture(0, "v1", "", 0)
    )

    def mutate(_argv, cwd: Path, _timeout):
        (cwd / "index.html").write_text("generated")
        (cwd / "penflow/code-ir.json").write_text("weakened")
        return ProcessCapture(0, "", "", 0)

    monkeypatch.setattr(witness_generation, "run_process", mutate)
    result = run_generation_trial(
        "ui-form",
        "codex",
        prepared_ui_candidate=candidate,
        report_path=tmp_path / "report.json",
        max_attempts=1,
    )
    assert result.outcome == "invalid" and result.evaluation is None
    assert result.attempts == 1 and candidate.exists()
    assert (tmp_path / "report-evidence/previous-index.html").read_text() == "previous"


def test_prepared_source_preserves_candidate_when_execution_control_is_incomplete(
    tmp_path,
    monkeypatch,
):
    candidate = tmp_path / "consumer"
    candidate.mkdir()
    for name in witness_prepared_ui.NORMATIVE:
        path = candidate / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("frozen")
    monkeypatch.setattr(witness_prepared_ui.shutil, "which", lambda _: "codex")
    monkeypatch.setattr(witness_prepared_ui, "_penflow_executable", lambda: "penflow")
    monkeypatch.setattr(witness_prepared_ui, "_design_authority", lambda *args: True)
    monkeypatch.setattr(
        witness_prepared_ui, "run_process", lambda *a: ProcessCapture(0, "v1", "", 0)
    )
    monkeypatch.setattr(
        witness_generation,
        "run_process",
        lambda *a: ProcessCapture(0, "", "", 0, control_complete=False),
    )
    result = run_generation_trial(
        "ui-form", "codex", prepared_ui_candidate=candidate, report_path=tmp_path / "report.json"
    )
    assert result.outcome == "evidence_incomplete" and result.evaluation is None
    assert result.retained_workspace and candidate.exists()
