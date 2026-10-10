"""Conflicting native review actions are rejected before progression can ignore them."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.review_support import grounded_response, reviewed_project
from validator.cli import app
from validator.semantic.review_api import prepare_feature_review


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


@pytest.mark.parametrize("action", ("--prepare-review", "--ingest-review"))
@pytest.mark.parametrize("stage", ("plan", "implement"))
def test_review_action_cannot_be_silently_ignored_by_ready_progression(
    tmp_path: Path, action: str, stage: str
) -> None:
    feature = reviewed_project(tmp_path)
    value = "plan" if action == "--prepare-review" else str(tmp_path / "not-read.json")
    before = _snapshot(tmp_path)
    result = CliRunner().invoke(
        app, ["validate", str(feature), "--progression", stage, action, value]
    )
    assert result.exit_code == 1, result.output
    assert (
        "--progression cannot be combined with --prepare-review or --ingest-review" in result.output
    )
    assert "Progression: READY" not in result.output
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("action", ("--prepare-review", "--ingest-review"))
def test_conflict_is_rejected_before_project_resolution_or_other_writing_modes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, action: str
) -> None:
    calls: list[Path | None] = []

    def resolve(path: Path | None) -> Path:
        calls.append(path)
        raise AssertionError("Project access must not precede option validation")

    monkeypatch.setattr("validator.cli._require_specs_root", resolve)
    value = "spec" if action == "--prepare-review" else str(tmp_path / "raw.json")
    result = CliRunner().invoke(
        app,
        [
            "validate",
            str(tmp_path),
            "--state-files",
            "--migrate",
            "--progression",
            "plan",
            action,
            value,
        ],
    )
    assert result.exit_code == 1
    assert "--progression cannot be combined" in result.output
    assert calls == []
    assert not tuple(tmp_path.iterdir())


def test_native_review_and_progression_still_work_as_separate_actions(tmp_path: Path) -> None:
    feature = reviewed_project(tmp_path)
    runner = CliRunner()
    prepared = runner.invoke(app, ["validate", str(feature), "--prepare-review", "plan"])
    assert prepared.exit_code == 0, prepared.output
    assert json.loads(prepared.output)["prepared"]["requirements"]
    bundle = tmp_path / "raw.json"
    bundle.write_text(
        json.dumps(
            {
                "raw_results": [
                    grounded_response(prepare_feature_review(tmp_path, feature.name, "plan"))
                ]
            }
        )
    )
    ingested = runner.invoke(app, ["validate", str(feature), "--ingest-review", str(bundle)])
    assert ingested.exit_code == 0, ingested.output
    assert Path(json.loads(ingested.output)["receipt_path"]).is_file()
    progressed = runner.invoke(app, ["validate", str(feature), "--progression", "implement"])
    assert progressed.exit_code == 0, progressed.output
    assert "Progression: READY" in progressed.output
