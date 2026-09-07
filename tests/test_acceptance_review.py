"""Actual prepare/ingest transport and documentary dependency freshness."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.acceptance_review_support import add_documentary_acceptance
from tests.review_support import grounded_response, reviewed_project
from validator.cli import app
from validator.semantic.acceptance_review import prepare_acceptance_review, verify_acceptance_review
from validator.semantic.review_api import verify_feature_review


def test_documentary_prepare_ingest_cli_is_distinct_and_current(tmp_path: Path):
    feature = "001-test"
    directory = reviewed_project(tmp_path, feature)
    receipt = add_documentary_acceptance(tmp_path, feature)
    runner = CliRunner()
    prepared = runner.invoke(
        app,
        ["validate", str(directory), "--prepare-review", "acceptance", "--model", "reviewer/v1"],
    )
    assert prepared.exit_code == 0, prepared.output
    context = prepare_acceptance_review(tmp_path, feature, "reviewer/v1")
    assert context.dependencies["review_purpose"] == "acceptance"
    assert context.requirement_scope == (f"{feature}:AC-002",)
    bundle = tmp_path / "raw-review.json"
    bundle.write_text(json.dumps({"raw_results": [grounded_response(context)]}))
    ingested = runner.invoke(
        app,
        [
            "validate",
            str(directory),
            "--ingest-review",
            str(bundle),
            "--review-kind",
            "acceptance",
            "--model",
            "reviewer/v1",
        ],
    )
    assert ingested.exit_code == 0, ingested.output
    assert verify_acceptance_review(tmp_path, feature, receipt, model="reviewer/v1")
    assert not verify_feature_review(tmp_path, feature, receipt, model="reviewer/v1")


def test_documentary_review_rejects_changed_input_and_new_unrelated_spec(tmp_path: Path):
    directory = reviewed_project(tmp_path)
    receipt = add_documentary_acceptance(tmp_path, directory.name)
    (tmp_path / "migration.md").write_text("All legacy contracts were changed.\n")
    with pytest.raises(ValueError, match="acceptance_input_stale"):
        verify_acceptance_review(tmp_path, directory.name, receipt, model="reviewer/v1")
    foreign = tmp_path / ".specs/features/002-other/spec.md"
    foreign.parent.mkdir()
    foreign.write_text("# Other\n## AC-001\nUnrelated obligation.\n")
    with pytest.raises(ValueError, match="acceptance_feature_inventory"):
        prepare_acceptance_review(tmp_path, directory.name, "reviewer/v1")


def test_generated_registry_is_provenance_unless_explicitly_required(tmp_path: Path):
    import hashlib

    from validator.semantic.acceptance_review import ingest_acceptance_review

    directory = reviewed_project(tmp_path)
    receipt = add_documentary_acceptance(tmp_path, directory.name)
    registry = tmp_path / ".specs/README.md"
    registry.write_text("Before finalization.\n")
    manifest_path = directory / ".reviews/doc-inputs.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["current_hashes"][".specs/README.md"] = hashlib.sha256(
        registry.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    prepared = prepare_acceptance_review(tmp_path, directory.name, "reviewer/v1")
    ingest_acceptance_review(
        tmp_path, directory.name, [grounded_response(prepared)], model="reviewer/v1"
    )
    registry.write_text("After finalization.\n")
    assert verify_acceptance_review(tmp_path, directory.name, receipt, model="reviewer/v1")
    manifest["source_paths"].append(".specs/README.md")
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match=r"acceptance_input_stale:\.specs/README\.md"):
        prepare_acceptance_review(tmp_path, directory.name, "reviewer/v1")
