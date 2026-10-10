"""Current semantic receipts have the same authority at both progression boundaries."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.test_gate_review_evidence import _raw, _save
from validator.cli import app


@pytest.mark.parametrize("gap", ["ambiguous", "unapproved_scope", "covered"])
def test_real_receipt_same_verdict_at_direct_and_pipeline_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    gap: str,
) -> None:
    from typer.testing import CliRunner

    from validator.cli import app
    from validator.semantic.review_files import prepare_feature_review

    monkeypatch.chdir(tmp_path)
    feature = _purge_project(tmp_path)
    prepared = prepare_feature_review(tmp_path, feature.name, "spec", "reviewer-v1")
    response = json.loads(
        _raw(prepared, disposition="ambiguous" if gap == "ambiguous" else "covered")
    )
    if gap == "unapproved_scope":
        source = next(s for s in prepared.sections if s.role == "spec")
        response["extra_scope"] = [
            {
                "description": "Email file contents.",
                "justification": "",
                "approved": False,
                "citations": [{"section_id": source.section_id, "excerpt": source.text}],
            }
        ]
    _save(feature, prepared, json.dumps(response))
    runner = CliRunner()
    direct = runner.invoke(
        app,
        ["validate", str(feature), "--progression", "plan", "--model", "reviewer-v1"],
        catch_exceptions=False,
    )
    assert runner.invoke(app, ["pipeline", "init", "--feature", feature.name]).exit_code == 0
    nested = _start_plan(runner, feature)
    assert direct.exit_code == nested.exit_code == (0 if gap == "covered" else 1)
    if gap != "covered":
        assert "blocking_spec_review_findings" in direct.output
        assert "blocking_spec_review_findings" in nested.output
        assert "| Plan | Pending |" in (feature / "pipeline.md").read_text()


def _purge_project(tmp_path: Path) -> Path:
    specs = tmp_path / ".specs"
    feature = specs / "features" / "001-purge"
    feature.mkdir(parents=True)
    (specs / "stacks").mkdir()
    (specs / "constitution.md").write_text("Only administrators may delete files.")
    (specs / "project.md").write_text("A local file utility.")
    (specs / "stacks/_default.md").write_text("Python 3.11.")
    (feature / "spec.md").write_text("FR-001: Delete files aged at least 24 hours.")
    return feature


def _start_plan(runner: CliRunner, feature: Path):
    return runner.invoke(
        app,
        [
            "pipeline",
            "update",
            "--feature",
            feature.name,
            "--phase",
            "plan",
            "--status",
            "in_progress",
            "--model",
            "reviewer-v1",
        ],
        catch_exceptions=False,
    )
