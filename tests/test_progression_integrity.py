"""Actual direct/native/pipeline boundaries enforce the same current obligations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from typer.testing import CliRunner

from tests.review_support import grounded_response, review_existing_project, reviewed_project
from validator.cli import app
from validator.pre_impl_analysis import analyze_feature_artifacts, has_blocking_findings
from validator.review_source_identity import prepared_sources_current
from validator.semantic.review_api import prepare_feature_review, verify_feature_review


def test_native_prepare_and_ingest_feed_direct_and_nested_gate(tmp_path, monkeypatch):
    feature = reviewed_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    _prepare_and_ingest_plan_review(tmp_path, feature, runner)
    direct = runner.invoke(app, ["validate", str(feature), "--progression", "implement"])
    assert direct.exit_code == 0, direct.output
    runner.invoke(app, ["pipeline", "init", "--feature", "001-test"])
    nested = runner.invoke(
        app,
        [
            "pipeline",
            "update",
            "--feature",
            "001-test",
            "--phase",
            "implement",
            "--status",
            "in_progress",
        ],
    )
    assert nested.exit_code == 0, nested.output
    (feature / "plan.md").write_text("FR-001 AC-001 Keep every file forever.\n")
    assert (
        runner.invoke(app, ["validate", str(feature), "--progression", "implement"]).exit_code == 1
    )
    assert (
        runner.invoke(
            app,
            [
                "pipeline",
                "update",
                "--feature",
                "001-test",
                "--phase",
                "implement",
                "--status",
                "done",
            ],
        ).exit_code
        == 1
    )


def _prepare_and_ingest_plan_review(tmp_path: Path, feature: Path, runner: CliRunner) -> None:
    prepared = runner.invoke(app, ["validate", str(feature), "--prepare-review", "plan"])
    assert prepared.exit_code == 0, prepared.output
    assert json.loads(prepared.output)["prepared"]["requirements"]
    bundle = tmp_path / "raw.json"
    bundle.write_text(
        json.dumps(
            {
                "raw_results": [
                    grounded_response(prepare_feature_review(tmp_path, "001-test", "plan"))
                ]
            }
        )
    )
    ingested = runner.invoke(app, ["validate", str(feature), "--ingest-review", str(bundle)])
    assert ingested.exit_code == 0, ingested.output


def test_skip_cannot_erase_required_clarification(tmp_path, monkeypatch):
    reviewed_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(app, ["pipeline", "init", "--feature", "001-test"])
    result = runner.invoke(
        app,
        [
            "pipeline",
            "update",
            "--feature",
            "001-test",
            "--phase",
            "clarify",
            "--status",
            "skipped",
        ],
    )
    assert result.exit_code == 1
    assert "cannot_be_skipped" in result.output


def test_config_model_change_invalidates_review(tmp_path, monkeypatch):
    feature = reviewed_project(tmp_path)
    prepared = prepare_feature_review(tmp_path, "001-test", "plan")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".specs/semantic/config.yaml").write_text("review_model: reviewer/v2\n")
    result = CliRunner().invoke(app, ["validate", str(feature), "--progression", "plan"])
    assert result.exit_code == 1
    assert "clarify_not_ready" in result.output
    old_context = analyze_feature_artifacts(
        feature, tmp_path / ".specs/constitution.md", prepared_review=prepared
    )
    assert old_context.semantic_status == "incomplete"
    assert has_blocking_findings(old_context)


def test_file_review_preserves_crlf_hashes_citations_and_freshness(tmp_path):
    feature = reviewed_project(tmp_path)
    spec = feature / "spec.md"
    raw = spec.read_bytes().replace(b"\n", b"\r\n")
    spec.write_bytes(raw)
    config = tmp_path / ".specs/semantic/config.yaml"
    config.write_bytes(b"review_model: reviewer/v1\r\n")
    review_existing_project(tmp_path, "001-test")
    prepared = prepare_feature_review(tmp_path, "001-test", "plan")
    key = ".specs/features/001-test/spec.md"
    assert prepared.source_hashes[key] == hashlib.sha256(raw).hexdigest()
    assert (
        prepared.dependencies["semantic_config"] == hashlib.sha256(config.read_bytes()).hexdigest()
    )
    assert (
        "".join(section.text for section in prepared.sections if section.source == key).encode()
        == raw
    )
    assert prepared_sources_current(prepared, feature, tmp_path / ".specs/constitution.md")
    receipt = feature / ".reviews/plan.json"
    assert verify_feature_review(tmp_path, "001-test", receipt)
    spec.write_bytes(raw.replace(b"\r\n", b"\n"))
    assert not prepared_sources_current(prepared, feature, tmp_path / ".specs/constitution.md")
    assert not verify_feature_review(tmp_path, "001-test", receipt)


def test_fresh_semantic_coverage_accepts_paraphrase_without_literal_id_references(
    tmp_path, monkeypatch
):
    feature = reviewed_project(tmp_path)
    (feature / "plan.md").write_text("# Plan\nDelete files once older than 24 hours.\n")
    review_existing_project(tmp_path, "001-test")
    constitution = tmp_path / ".specs/constitution.md"
    report = analyze_feature_artifacts(feature, constitution)
    assert report.semantic_status == "covered"
    assert report.coverage_percent == 0
    assert not has_blocking_findings(report)
    assert has_blocking_findings(
        analyze_feature_artifacts(feature, constitution, structural_only=True)
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert (
        runner.invoke(app, ["validate", str(feature), "--progression", "implement"]).exit_code == 0
    )
    (feature / "plan.md").write_text("# Plan\nKeep files forever.\n")
    assert (
        runner.invoke(app, ["validate", str(feature), "--progression", "implement"]).exit_code == 1
    )


def test_clarification_cli_persists_current_answer_and_rejects_stale_replay(tmp_path, monkeypatch):
    feature = reviewed_project(tmp_path)
    spec = feature / "spec.md"
    spec.write_text(spec.read_text().replace("after 24 hours", "after TBD hours"))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["validate", str(feature), "--clarify"])
    assert result.exit_code == 1
    inventory = json.loads(result.output)
    question = inventory["inventory"][0]
    answer = tmp_path / "answer.json"
    answer.write_text(
        json.dumps(
            {
                "requirement_id": question["requirement_id"],
                "decision_key": question["decision_key"],
                "source_hash": inventory["source_hash"],
                "answer": "Delete files after 24 hours.",
            }
        )
    )
    accepted = runner.invoke(app, ["validate", str(feature), "--clarification-answer", str(answer)])
    assert accepted.exit_code == 0, accepted.output
    assert "## Clarifications" in spec.read_text()
    assert "Delete files after 24 hours." in spec.read_text()
    assert json.loads(accepted.output)["source_hash"] != inventory["source_hash"]
    replay = runner.invoke(app, ["validate", str(feature), "--clarification-answer", str(answer)])
    assert replay.exit_code == 1
    assert "clarification_answer_stale" in replay.output
    assert runner.invoke(app, ["validate", str(feature), "--progression", "plan"]).exit_code == 1
