"""CLI tests for `livespec validate --pre-impl` (Feature B — read-only proof).

Protected invariants:
- Exit 1 iff any finding is CRITICAL or HIGH (H3); exit 0 otherwise.
- The branch is read-only: it creates NO file under the feature directory (no
  checks/, no changelog, no source writes).
- JSON output carries findings/coverage/metrics.
"""

# 070-analyze-gate anchors: @spec(FR-001) @spec(FR-008) @spec(FR-010)

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app

runner = CliRunner()


def _snapshot(directory: Path) -> set[Path]:
    return set(directory.rglob("*"))


@pytest.fixture()
def feature_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    specs = tmp_path / ".specs"
    specs.mkdir()
    (specs / "constitution.md").write_text(
        "# Constitution\n\n- Keep it simple.\n", encoding="utf-8"
    )
    fdir = specs / "features" / "001-feature"
    fdir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return fdir


def test_pre_impl_json_exits_1_on_high_and_writes_nothing(feature_dir: Path) -> None:
    (feature_dir / "spec.md").write_text(
        "## Functional Requirements\n- FR-001: Export CSV.\n- FR-002: Email report.\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "## Implementation Plan\n- Build FR-001 exporter.\n",
        encoding="utf-8",
    )
    before = _snapshot(feature_dir)

    import json

    result = runner.invoke(
        app,
        ["validate", "--pre-impl", "--format", "json", str(feature_dir)],
        catch_exceptions=False,
    )

    assert result.exit_code == 1  # FR-002 uncovered = HIGH
    data = json.loads(result.output)
    assert set(data.keys()) >= {"findings", "coverage", "metrics"}
    assert data["metrics"]["coverage_percent"] == 50.0
    # Read-only: no file created under the feature dir (no checks/, no changelog).
    assert _snapshot(feature_dir) == before


def test_pre_impl_exits_0_when_no_critical_or_high(feature_dir: Path) -> None:
    (feature_dir / "spec.md").write_text(
        "## Functional Requirements\n- FR-001: Export CSV.\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "## Implementation Plan\n- Build FR-001 exporter.\n",
        encoding="utf-8",
    )
    before = _snapshot(feature_dir)

    result = runner.invoke(
        app,
        ["validate", "--pre-impl", "--format", "json", str(feature_dir)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert _snapshot(feature_dir) == before


def test_pre_impl_markdown_renders_report_heading(feature_dir: Path) -> None:
    (feature_dir / "spec.md").write_text(
        "## Functional Requirements\n- FR-001: Export CSV.\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "## Implementation Plan\n- Build FR-001 exporter.\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["validate", "--pre-impl", str(feature_dir)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "## Specification Analysis Report" in result.output
