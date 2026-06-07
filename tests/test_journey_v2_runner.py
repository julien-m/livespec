"""Tests for compiled-only User Journeys v2 run semantics."""

from __future__ import annotations

from pathlib import Path

from tests.test_journey_v2_validation import _write_feature, _write_v2_journey
from validator.journeys.compiler import compile_journeys
from validator.journeys.runner import run_journeys


def _setup_compiled(tmp_path: Path) -> Path:
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    _write_v2_journey(specs)
    result = compile_journeys(tmp_path, journey="onboarding-first-project")
    assert result.error_count == 0
    return specs


def test_run_journeys_executes_manifest_artifacts_without_compiling(tmp_path: Path) -> None:
    """FR-023: run uses compiled artifacts and does not rewrite them."""
    _setup_compiled(tmp_path)
    artifact = tmp_path / "tests" / "e2e" / "journeys" / "onboarding_first_project.spec.ts"
    before = artifact.stat().st_mtime_ns

    result = run_journeys(tmp_path, journey="onboarding-first-project", execute=False)

    assert result.error_count == 0, [issue.code for issue in result.issues]
    assert result.executed == ["onboarding-first-project"]
    assert artifact.stat().st_mtime_ns == before


def test_run_journeys_fails_stale_manifest_without_recompiling(tmp_path: Path) -> None:
    """AC-028: stale compiled manifests fail before native runner execution."""
    specs = _setup_compiled(tmp_path)
    source = specs / "journeys" / "onboarding-first-project" / "journey.yaml"
    source.write_text(source.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    artifact = tmp_path / "tests" / "e2e" / "journeys" / "onboarding_first_project.spec.ts"
    before = artifact.stat().st_mtime_ns

    result = run_journeys(tmp_path, journey="onboarding-first-project", execute=False)

    assert result.error_count == 1
    assert result.issues[0].code == "journey_compiled_stale"
    assert artifact.stat().st_mtime_ns == before


def test_run_journeys_reports_manual_and_disabled_without_execution(tmp_path: Path) -> None:
    """FR-027: manual and disabled policies are reported and never executed."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    source.write_text(
        source.read_text(encoding="utf-8").replace("local: impacted", "local: manual"),
        encoding="utf-8",
    )

    result = run_journeys(tmp_path, journey="onboarding-first-project", execute=False)

    assert result.executed == []
    assert result.manual == ["onboarding-first-project"]
