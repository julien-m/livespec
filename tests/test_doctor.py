"""Tests for the project-level LiveSpec doctor command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from pytest import MonkeyPatch
from typer.testing import CliRunner

from validator.cli import app
from validator.doctor.models import JsonValue

runner = CliRunner()


def _json_report(output: str) -> dict[str, JsonValue]:
    data = json.loads(output)
    assert isinstance(data, dict)
    return cast(dict[str, JsonValue], data)


def _finding_codes(report: dict[str, JsonValue]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    codes: set[str] = set()
    for finding in findings:
        assert isinstance(finding, dict)
        code = finding.get("code")
        assert isinstance(code, str)
        codes.add(code)
    return codes


def _write_feature(
    specs: Path,
    feature: str = "001-auth",
    *,
    status: str = "Implemented",
    metadata: str = "",
    implementation: str | None = None,
) -> Path:
    """Create a minimal feature directory for doctor fixtures."""
    feature_dir = specs / "features" / feature
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text(
        f"---\nstatus: {status}\n{metadata}---\n# Auth\n\n"
        "## Acceptance Criteria\n\n- **AC-001:** Login works.\n"
    )
    if implementation is not None:
        (feature_dir / "implementation.md").write_text(implementation)
    return feature_dir


def test_doctor_json_reports_stale_mapping_missing_test_and_hook(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Doctor reports real health failures beyond structural validation."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    (specs / "roadmap.md").write_text("- [x] [Auth](features/001-auth/)\n")
    (specs / "README.md").write_text("| [001-auth](features/001-auth/) | Implemented |\n")
    _write_feature(
        specs,
        implementation=(
            "# Implementation\n\n"
            "## Requirement Mapping\n\n"
            "| Requirement | File(s) | @spec Anchor | Status | Last Verified |\n"
            "|---|---|---|---|---|\n"
            "| FR-001 | `src/auth.py` | `@spec FR-001` | Implemented | 2026-06-02 |\n\n"
            "## Acceptance Criteria Mapping\n\n"
            "| AC | Test File | Status |\n"
            "|---|---|---|\n"
            "| AC-001 | `tests/test_auth.py` | Implemented |\n"
        ),
    )

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["doctor", "--format", "json"])

    assert result.exit_code == 1
    report = _json_report(result.output)
    codes = _finding_codes(report)
    assert report["status"] == "FAIL"
    assert "mapping_stale" in codes
    assert "missing_test_file" in codes
    assert "hook_unenforced" in codes


def test_doctor_strict_promotes_runner_warning_to_failure(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Strict mode fails when mapped tests exist but no runner includes them."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    (specs / "roadmap.md").write_text("- [x] [Auth](features/001-auth/)\n")
    (specs / "README.md").write_text("| [001-auth](features/001-auth/) | Implemented |\n")
    tests_dir = tmp_path / "AppUITests" / "Journeys"
    tests_dir.mkdir(parents=True)
    (tests_dir / "Login.swift").write_text("final class LoginJourney {}\n")
    _write_feature(
        specs,
        implementation=(
            "# Implementation\n\n"
            "## Acceptance Criteria Mapping\n\n"
            "| AC | Test File | Status |\n"
            "|---|---|---|\n"
            "| AC-001 | `AppUITests/Journeys/Login.swift` | Implemented |\n"
        ),
    )

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["doctor", "--strict", "--format", "json"])

    assert result.exit_code == 1
    report = _json_report(result.output)
    assert "test_not_in_runner" in _finding_codes(report)


def test_doctor_fix_plan_is_read_only(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """The cleanup plan mode reports proposed actions without modifying files."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    (specs / "roadmap.md").write_text("- [x] [Auth](features/001-auth/)\n")
    (specs / "README.md").write_text("| [001-auth](features/001-auth/) | Implemented |\n")
    _write_feature(specs, implementation="# Implementation\n")
    orphan = specs / "design" / "baselines" / "999-ghost" / "screen.png"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("png")
    before = {
        path.relative_to(tmp_path): path.read_text()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["doctor", "--fix-plan"])

    after = {
        path.relative_to(tmp_path): path.read_text()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert result.exit_code == 1
    assert before == after
    assert "visual_orphan" in result.output


def test_doctor_apply_cleanup_refuses_destructive_actions(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Apply cleanup never deletes active specs, tests, or evidence."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    (specs / "roadmap.md").write_text("- [x] [Auth](features/001-auth/)\n")
    (specs / "README.md").write_text("| [001-auth](features/001-auth/) | Implemented |\n")
    _write_feature(specs, implementation="# Implementation\n")
    orphan = specs / "design" / "baselines" / "999-ghost" / "screen.png"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("png")

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["doctor", "--apply-cleanup", "--format", "json"])

    assert result.exit_code == 1
    assert orphan.exists()
    report = _json_report(result.output)
    cleanup_actions = report["cleanup_actions"]
    assert isinstance(cleanup_actions, list)
    assert any(
        isinstance(action, dict) and action.get("refused") is True
        for action in cleanup_actions
    )


def test_doctor_lifecycle_allows_linked_supersession_only(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Linked deprecated specs are allowed; unlinked ones produce a finding."""
    specs = tmp_path / ".specs"
    specs.mkdir()
    (specs / "roadmap.md").write_text("- [x] [Old](features/001-old/)\n")
    (specs / "README.md").write_text("| [001-old](features/001-old/) | Deprecated |\n")
    _write_feature(specs, "001-old", status="Deprecated")
    _write_feature(
        specs,
        "002-linked",
        status="Deprecated",
        metadata="superseded_by: 003-new\n",
    )

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["doctor", "--format", "json"])

    assert result.exit_code == 1
    report = _json_report(result.output)
    assert "supersession_missing" in _finding_codes(report)
    lifecycle_findings = [
        finding
        for finding in report["findings"]
        if isinstance(finding, dict) and finding.get("code") == "supersession_missing"
    ]
    assert [finding.get("feature") for finding in lifecycle_findings] == ["001-old"]


def test_spec_doctor_skill_distinguishes_doctor_from_validate() -> None:
    """The skill explains doctor health, validate, and R3.2 traceability."""
    skill_path = Path(__file__).parents[1] / ".agent-sync" / "skills" / "spec-doctor" / "SKILL.md"
    content = skill_path.read_text()

    assert "$spec-doctor" in content
    assert "project health audit" in content
    assert "validate" in content
    assert "lower-level spec validator" in content
    assert "R3.2" in content
    assert "@spec(FR-xxx)" in content
