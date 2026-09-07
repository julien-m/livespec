"""Missing canonical inputs remain read-only, structured Analyze failures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.review_support import reviewed_project
from validator.cli import app


def _snapshot(root: Path) -> dict[str, bytes | None]:
    return {
        str(path.relative_to(root)): path.read_bytes() if path.is_file() else None
        for path in root.rglob("*")
    }


@pytest.mark.parametrize("missing", [("spec.md",), ("plan.md",), ("spec.md", "plan.md")])
@pytest.mark.parametrize("mode", [[], ["--no-review"], ["--structural-only"]])
@pytest.mark.parametrize("invalid_review_config", [False, True])
def test_missing_canonical_inputs_return_critical_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    missing: tuple[str, ...],
    mode: list[str],
    invalid_review_config: bool,
) -> None:
    feature = tmp_path / ".specs/features/001-export"
    feature.mkdir(parents=True)
    for name in {"spec.md", "plan.md"} - set(missing):
        (feature / name).write_text("# Export\nFR-001: Export CSV.\n")
    if invalid_review_config:
        semantic = tmp_path / ".specs/semantic"
        semantic.mkdir()
        (semantic / "config.yaml").write_text("review_max_chars: invalid\n")
    monkeypatch.chdir(tmp_path)
    before = _snapshot(tmp_path)

    result = CliRunner().invoke(
        app,
        ["validate", "--pre-impl", "--format", "json", *mode, str(feature)],
        catch_exceptions=False,
    )

    assert result.exit_code == 1
    data = json.loads(result.output)
    artifacts = [item for item in data["findings"] if item["category"] == "artifact"]
    assert {tuple(item["locations"]) for item in artifacts} == {(name,) for name in missing}
    assert all(item["severity"] == "CRITICAL" for item in artifacts)
    assert data["metrics"]["critical_count"] == len(missing)
    expected_status = "not_requested" if "--structural-only" in mode else "incomplete"
    assert data["semantic_status"] == expected_status
    assert data["coverage_kind"] == "structural_reference"
    assert not any(item["category"] == "semantic" for item in data["findings"])
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("mode", [[], ["--no-review"]])
@pytest.mark.parametrize("has_receipt", [True, False])
def test_complete_inputs_still_require_current_semantic_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: list[str],
    has_receipt: bool,
) -> None:
    feature = reviewed_project(tmp_path)
    if not has_receipt:
        (feature / ".reviews/plan.json").unlink()
    monkeypatch.chdir(tmp_path)
    before = _snapshot(tmp_path)

    result = CliRunner().invoke(
        app,
        ["validate", "--pre-impl", "--format", "json", *mode, str(feature)],
        catch_exceptions=False,
    )

    assert result.exit_code == (0 if has_receipt else 1)
    data = json.loads(result.output)
    assert data["semantic_status"] == ("covered" if has_receipt else "incomplete")
    assert data["metrics"]["high_count"] == (0 if has_receipt else 1)
    assert data["coverage_percent"] == 100
    assert _snapshot(tmp_path) == before
