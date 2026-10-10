"""Structural diagnostics cannot be ignored by earlier validation actions."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.review_support import reviewed_project
from validator.cli import app

TERMINAL_ACTIONS = (
    ("--progression", "plan"),
    ("--prepare-review", "plan"),
    ("--ingest-review", "missing-review.json"),
    ("--clarify",),
    ("--clarification-answer", "missing-answer.json"),
    ("--state-files",),
    ("--state-files", "--migrate"),
)


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


@pytest.mark.parametrize("action", ((), *TERMINAL_ACTIONS))
def test_structural_only_requires_pre_impl_before_any_other_dispatch(
    tmp_path: Path, action: tuple[str, ...]
) -> None:
    feature = reviewed_project(tmp_path)
    before = _snapshot(tmp_path)
    result = CliRunner().invoke(app, ["validate", str(feature), "--structural-only", *action])
    assert result.exit_code == 1, result.output
    assert "Error: --structural-only requires --pre-impl" in result.output
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("action", TERMINAL_ACTIONS)
def test_structural_pre_impl_rejects_earlier_terminal_actions_without_project_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, action: tuple[str, ...]
) -> None:
    calls: list[Path | None] = []

    def resolve(path: Path | None) -> Path:
        calls.append(path)
        raise AssertionError("Option conflict must be resolved before project access")

    monkeypatch.setattr("validator.cli._require_specs_root", resolve)
    result = CliRunner().invoke(
        app, ["validate", str(tmp_path), "--pre-impl", "--structural-only", *action]
    )
    assert result.exit_code == 1
    assert "Error: --structural-only cannot be combined with" in result.output
    assert calls == []
    assert not tuple(tmp_path.iterdir())


def test_structural_pre_impl_still_runs_actual_read_only_diagnostic(tmp_path: Path) -> None:
    feature = reviewed_project(tmp_path)
    before = _snapshot(tmp_path)
    result = CliRunner().invoke(
        app, ["validate", str(feature), "--pre-impl", "--structural-only", "--format", "json"]
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["coverage_kind"] == "structural_reference"
    assert report["semantic_status"] == "not_requested"
    assert report["metrics"]["coverage_percent"] == 100.0
    assert _snapshot(tmp_path) == before
