"""Tests for validator.pipeline — pipeline state management CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app

runner = CliRunner()

PIPELINE_MD = """\
# Pipeline — 001-test

**Started:** 2026-04-10 12:00
**Flags:** none

| Phase | Status | Completed At |
|-------|--------|--------------|
| Specify | Pending | — |
| Spec Review | Pending | — |
| Clarify | Pending | — |
| Plan | Pending | — |
| Plan Review | Pending | — |
| Analyze | Pending | — |
| Preflight | Pending | — |
| Implement | Pending | — |
| Test | Pending | — |
"""

PIPELINE_MD_PADDED = """\
# Pipeline — 001-test

**Started:** 2026-04-10 12:00
**Flags:** none

| Phase | Status | Completed At |
|-------|--------|--------------|
|  Specify  |  Pending  |  —  |
|  Spec Review  |  Pending  |  —  |
|  Clarify  |  Pending  |  —  |
|  Plan  |  Pending  |  —  |
|  Plan Review  |  Pending  |  —  |
|  Analyze  |  Pending  |  —  |
|  Preflight  |  Pending  |  —  |
|  Implement  |  Pending  |  —  |
|  Test  |  Pending  |  —  |
"""


@pytest.fixture()
def specs_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    specs = tmp_path / ".specs"
    specs.mkdir()
    feature_dir = specs / "features" / "001-test"
    feature_dir.mkdir(parents=True)
    # Pipeline commands use find_specs_root() which starts from Path.cwd().
    # Change cwd to tmp_path so the CLI can discover the temporary .specs/ directory.
    monkeypatch.chdir(tmp_path)
    return specs


class TestPipelineInit:
    def test_creates_pipeline_md(self, specs_root: Path) -> None:
        feature_dir = specs_root / "features" / "001-test"
        result = runner.invoke(
            app, ["pipeline", "init", "--feature", "001-test"], catch_exceptions=False
        )
        assert result.exit_code == 0
        pipeline = feature_dir / "pipeline.md"
        assert pipeline.exists()
        content = pipeline.read_text()
        for phase in [
            "Specify",
            "Spec Review",
            "Clarify",
            "Plan",
            "Plan Review",
            "Analyze",
            "Preflight",
            "Implement",
            "Test",
        ]:
            assert f"| {phase} | Pending |" in content

    def test_preserves_quoted_description_and_flags(self, specs_root: Path) -> None:
        feature_dir = specs_root / "features" / "001-test"
        description = (
            "Professional desktop booking operations dashboard: build a professional "
            "SaaS booking operations dashboard"
        )
        result = runner.invoke(
            app,
            [
                "pipeline",
                "init",
                "--feature",
                "001-test",
                "--description",
                description,
                "--flags",
                "--auto --mono",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        content = (feature_dir / "pipeline.md").read_text()
        assert "**Flags:** `--auto --mono`" in content
        assert f"**Feature Description:** {description}" in content
        assert "| Specify | Pending |" in content

    def test_error_if_feature_not_found(self, specs_root: Path) -> None:
        result = runner.invoke(app, ["pipeline", "init", "--feature", "999-nonexistent"])
        assert result.exit_code != 0


class TestPipelineUpdate:
    def test_update_sets_status(self, specs_root: Path) -> None:
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(PIPELINE_MD)
        result = runner.invoke(
            app,
            [
                "pipeline",
                "update",
                "--feature",
                "001-test",
                "--phase",
                "specify",
                "--status",
                "in_progress",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "In Progress" in pipeline_path.read_text()

    def test_update_padded_table_rows(self, specs_root: Path) -> None:
        """AI-generated tables may have extra whitespace padding around cell values."""
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(PIPELINE_MD_PADDED)
        result = runner.invoke(
            app,
            [
                "pipeline",
                "update",
                "--feature",
                "001-test",
                "--phase",
                "specify",
                "--status",
                "done",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Done" in pipeline_path.read_text()

    def test_update_is_idempotent(self, specs_root: Path) -> None:
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(PIPELINE_MD)
        runner.invoke(
            app,
            [
                "pipeline",
                "update",
                "--feature",
                "001-test",
                "--phase",
                "specify",
                "--status",
                "done",
            ],
        )
        content_after_first = pipeline_path.read_text()
        runner.invoke(
            app,
            [
                "pipeline",
                "update",
                "--feature",
                "001-test",
                "--phase",
                "specify",
                "--status",
                "done",
            ],
        )
        assert pipeline_path.read_text() == content_after_first

    def test_update_unknown_phase_exits_1(self, specs_root: Path) -> None:
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(PIPELINE_MD)
        result = runner.invoke(
            app,
            [
                "pipeline",
                "update",
                "--feature",
                "001-test",
                "--phase",
                "nonexistent",
                "--status",
                "done",
            ],
        )
        assert result.exit_code != 0
        assert pipeline_path.read_text() == PIPELINE_MD  # File must not be mutated


class TestPipelineRead:
    # @spec(FR-001): analyze phase present in PHASE_ORDER (070-analyze-gate)
    def test_outputs_json_for_all_phases(self, specs_root: Path) -> None:
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(PIPELINE_MD)
        result = runner.invoke(
            app, ["pipeline", "read", "--feature", "001-test"], catch_exceptions=False
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert set(data.keys()) == {
            "specify",
            "spec-review",
            "clarify",
            "plan",
            "plan-review",
            "analyze",
            "preflight",
            "implement",
            "test",
        }
        assert data["specify"] == "Pending"


class TestPipelineNext:
    def test_returns_first_pending_exits_0(self, specs_root: Path) -> None:
        content = PIPELINE_MD.replace("| Specify | Pending |", "| Specify | Done |")
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(content)
        result = runner.invoke(
            app, ["pipeline", "next", "--feature", "001-test"], catch_exceptions=False
        )
        assert result.exit_code == 0
        assert result.output.strip() == "spec-review"

    def test_all_done_exits_2(self, specs_root: Path) -> None:
        """Exit 2 = pipeline complete (success state, not error)."""
        content = PIPELINE_MD
        for phase in [
            "Specify",
            "Spec Review",
            "Clarify",
            "Plan",
            "Plan Review",
            "Analyze",
            "Preflight",
            "Implement",
            "Test",
        ]:
            content = content.replace(f"| {phase} | Pending |", f"| {phase} | Done |")
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(content)
        result = runner.invoke(app, ["pipeline", "next", "--feature", "001-test"])
        assert result.exit_code == 2  # NOT 1 — all done is a success state

    def test_missing_pipeline_exits_1(self, specs_root: Path) -> None:
        result = runner.invoke(app, ["pipeline", "next", "--feature", "001-test"])
        assert result.exit_code == 1


# Legacy pipeline.md generated BEFORE the Clarify phase existed — no "| Clarify |" row.
LEGACY_PIPELINE_MD = """\
# Pipeline — 001-test

**Started:** 2026-04-10 12:00
**Flags:** none

| Phase | Status | Completed At |
|-------|--------|--------------|
| Specify | Done | 2026-04-10 12:01 |
| Spec Review | Done | 2026-04-10 12:02 |
| Plan | Pending | — |
| Plan Review | Pending | — |
| Preflight | Pending | — |
| Implement | Pending | — |
| Test | Pending | — |
"""

_PHASE_DISPLAYS = {
    "Specify",
    "Spec Review",
    "Clarify",
    "Plan",
    "Plan Review",
    "Analyze",
    "Preflight",
    "Implement",
    "Test",
}


def _phase_order_in_file(content: str) -> list[str]:
    order: list[str] = []
    for line in content.splitlines():
        if not line.startswith("|"):
            continue
        cell = line.split("|")[1].strip()
        if cell in _PHASE_DISPLAYS:
            order.append(cell)
    return order


class TestPipelineBackwardCompat:
    """C13: a new phase slug must not block legacy pipeline.md files missing its row."""

    def test_update_inserts_missing_clarify_row_at_correct_position(self, specs_root: Path) -> None:
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(LEGACY_PIPELINE_MD)
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
                "done",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0  # NOT 1 — legacy file must self-heal, not block
        content = pipeline_path.read_text()
        assert "| Clarify | Done |" in content
        order = _phase_order_in_file(content)
        # Inserted at the canonical PHASE_ORDER position (between Spec Review and Plan).
        assert order.index("Clarify") == order.index("Spec Review") + 1
        assert order.index("Clarify") == order.index("Plan") - 1

    def test_next_then_update_then_next_advances_past_clarify(self, specs_root: Path) -> None:
        pipeline_path = specs_root / "features" / "001-test" / "pipeline.md"
        pipeline_path.write_text(LEGACY_PIPELINE_MD)

        first = runner.invoke(
            app, ["pipeline", "next", "--feature", "001-test"], catch_exceptions=False
        )
        assert first.exit_code == 0
        assert first.output.strip() == "clarify"

        update = runner.invoke(
            app,
            [
                "pipeline",
                "update",
                "--feature",
                "001-test",
                "--phase",
                "clarify",
                "--status",
                "done",
            ],
            catch_exceptions=False,
        )
        assert update.exit_code == 0

        second = runner.invoke(
            app, ["pipeline", "next", "--feature", "001-test"], catch_exceptions=False
        )
        assert second.exit_code == 0
        assert second.output.strip() == "plan"
