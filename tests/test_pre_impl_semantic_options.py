"""Analyze rejects competing semantic actions before they can ignore it or write evidence."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.review_support import grounded_response, reviewed_project
from validator.clarify_gate import scan_clarification_opportunities
from validator.cli import app
from validator.semantic.review_api import prepare_feature_review

ACTIONS = (
    "--clarify",
    "--clarification-answer",
    "--prepare-review",
    "--ingest-review",
    "--progression",
)


def _snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _action_input(root: Path, feature: Path, action: str) -> list[str]:
    if action == "--clarify":
        return [action]
    if action in ("--prepare-review", "--progression"):
        return [action, "plan"]
    path = root / "input.json"
    if action == "--ingest-review":
        prepared = prepare_feature_review(root, feature.name, "plan")
        path.write_text(json.dumps({"raw_results": [grounded_response(prepared)]}))
        (feature / ".reviews/plan.json").unlink()
    else:
        spec = feature / "spec.md"
        spec.write_text(spec.read_text() + "\n## FR-002\nExport must be secure.\n")
        item = scan_clarification_opportunities(spec)[0]
        path.write_text(
            json.dumps(
                {
                    "requirement_id": item.requirement_id,
                    "decision_key": item.decision_key,
                    "source_hash": item.source_hash,
                    "answer": "Use TLS 1.3 for export transport.",
                }
            )
        )
    return [action, str(path)]


@pytest.mark.parametrize("action", ACTIONS)
def test_analyze_cannot_be_replaced_by_a_semantic_action_or_write(
    tmp_path: Path, action: str
) -> None:
    feature = reviewed_project(tmp_path)
    arguments = _action_input(tmp_path, feature, action)
    before = _snapshot(tmp_path)
    result = CliRunner().invoke(app, ["validate", str(feature), "--pre-impl", *arguments])
    assert _snapshot(tmp_path) == before
    assert result.exit_code == 1, result.output
    assert "Error: --pre-impl cannot be combined with" in result.output


@pytest.mark.parametrize("action", ACTIONS)
def test_analyze_conflict_precedes_project_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, action: str
) -> None:
    calls: list[Path | None] = []

    def resolve(path: Path | None) -> Path:
        calls.append(path)
        raise AssertionError("Project access must follow mode validation")

    monkeypatch.setattr("validator.cli._require_specs_root", resolve)
    arguments = [action] if action == "--clarify" else [action, "unused"]
    result = CliRunner().invoke(app, ["validate", str(tmp_path), "--pre-impl", *arguments])
    assert result.exit_code == 1
    assert "Error: --pre-impl cannot be combined with" in result.output
    assert calls == []
    assert not tuple(tmp_path.iterdir())


@pytest.mark.parametrize("flags", ((), ("--fix",), ("--smart",), ("--fix", "--smart")))
def test_valid_analyze_keeps_legacy_fix_flags_read_only(
    tmp_path: Path, flags: tuple[str, ...]
) -> None:
    feature = reviewed_project(tmp_path)
    before = _snapshot(tmp_path)
    result = CliRunner().invoke(
        app, ["validate", str(feature), "--pre-impl", "--format", "json", *flags]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["semantic_status"] == "covered"
    assert _snapshot(tmp_path) == before
