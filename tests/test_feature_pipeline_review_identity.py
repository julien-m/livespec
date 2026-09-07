"""Documented pipeline transitions preserve the caller's current review identity."""

import re
import shlex
from pathlib import Path

import pytest
from typer.core import TyperGroup
from typer.main import get_command
from typer.testing import CliRunner

from tests.review_support import grounded_response, reviewed_project
from validator.cli import app
from validator.semantic.review_api import ingest_feature_review, prepare_feature_review

SKILL = Path(__file__).parents[1] / ".agent-sync/skills/spec-feature/SKILL.md"


def _documented_command(phase: str, model: str, budget: int | None) -> list[str]:
    commands = re.findall(r"`(livespec pipeline update [^`]+)`", SKILL.read_text())
    command = next(value for value in commands if f"--phase {phase} " in value)
    optional = "[--review-max-chars <resolved-budget>]"
    command = command.replace(optional, f"--review-max-chars {budget}" if budget else "")
    command = command.replace("NNN-feature-name", "001-test").replace("<resolved-model>", model)
    return shlex.split(command)[1:]


@pytest.mark.parametrize("phase", ["clarify", "plan-review"])
@pytest.mark.parametrize("budget", [None, 23000])
def test_documented_updates_parse_actual_model_and_optional_budget(
    tmp_path: Path, phase: str, budget: int | None
) -> None:
    argv = _documented_command(phase, "reviewer/actual-v2", budget)
    if phase == "plan-review":
        assert "append `--review-result <review_result_path>`" in SKILL.read_text()
        argv += ["--review-result", str(tmp_path / "actual-review.json")]
    root = get_command(app)
    assert isinstance(root, TyperGroup)
    pipeline = root.commands["pipeline"]
    assert isinstance(pipeline, TyperGroup)
    with pipeline.commands["update"].make_context("update", argv[2:]) as context:
        assert context.params["model"] == "reviewer/actual-v2"
        assert context.params["review_max_chars"] == budget
        assert context.params["feature"] == "001-test"
        assert context.params["phase"] == phase
        assert context.params["status"] == "done"
        assert context.params["timestamp"] is True
        if phase == "plan-review":
            assert context.params["review_result"] == str(tmp_path / "actual-review.json")
    assert not list(tmp_path.iterdir())


def test_documented_clarify_update_uses_explicit_identity_and_rejects_other_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feature = reviewed_project(tmp_path)
    (tmp_path / ".specs/semantic/config.yaml").write_text("review_model: reviewer/fallback\n")
    prepared = prepare_feature_review(tmp_path, feature.name, "spec", "reviewer/actual-v2", 23000)
    receipt, _ = ingest_feature_review(
        tmp_path,
        feature.name,
        "spec",
        [grounded_response(prepared)],
        model="reviewer/actual-v2",
        max_chars=23000,
    )
    assert receipt.ready
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["pipeline", "init", "--feature", feature.name]).exit_code == 0
    pipeline = feature / "pipeline.md"
    before = pipeline.read_bytes()

    wrong = runner.invoke(app, _documented_command("clarify", "reviewer/wrong", 23000))
    assert wrong.exit_code == 1
    assert "clarify_not_ready" in wrong.output
    assert pipeline.read_bytes() == before
    accepted = runner.invoke(app, _documented_command("clarify", "reviewer/actual-v2", 23000))
    assert accepted.exit_code == 0, accepted.output
    assert "| Clarify | Done |" in pipeline.read_text()
