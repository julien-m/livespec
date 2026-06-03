"""Tests for executable user journey validation, compilation, and reporting."""

from __future__ import annotations

import json
from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from validator.cli import app
from validator.journeys import scan_journeys

runner = CliRunner()


def _make_specs(root: Path) -> Path:
    specs = root / ".specs"
    feature_dir = specs / "features" / "012-auth"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text(
        "---\nstatus: Implemented\n---\n"
        "# Auth\n\n"
        "## Acceptance Criteria\n\n"
        "- **AC-001:** Login works.\n"
        "- **AC-002:** Dashboard appears.\n\n"
        "## Functional Requirements\n\n"
        "- **FR-001:** Accept credentials.\n",
        encoding="utf-8",
    )
    return specs


def _write_journey(
    specs: Path,
    *,
    feature: str = "012-auth",
    journey_id: str = "login-happy-path",
    target: str = "web",
    extra: str = "",
) -> Path:
    journey_dir = specs / "journeys" / feature
    journey_dir.mkdir(parents=True, exist_ok=True)
    path = journey_dir / f"{journey_id}.journey.yaml"
    path.write_text(
        f"""id: {journey_id}
feature: {feature}
title: User can log in
run_policy: always
covers:
  ac: [AC-001, AC-002]
target:
  surface: {target}
steps:
  - open: "/login"
  - fill: {{ label: "Email", value: "user@example.com" }}
  - click: {{ role: "button", name: "Login" }}
  - wait: {{ seconds: 10, until: {{ text: "Dashboard" }} }}
  - assert: {{ text: "Dashboard" }}
{extra}""",
        encoding="utf-8",
    )
    return path


def test_journey_validate_accepts_valid_yaml(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """A canonical journey validates successfully."""
    specs = _make_specs(tmp_path)
    _write_journey(specs)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["journey", "validate"])

    assert result.exit_code == 0, result.output
    assert "valid=1" in result.output
    assert "warnings=0" in result.output


def test_journey_validate_rejects_unknown_action(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Unknown step actions fail with an actionable validation error."""
    specs = _make_specs(tmp_path)
    journey = _write_journey(specs)
    journey.write_text(
        journey.read_text(encoding="utf-8").replace("- click:", "- teleport:"),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["journey", "validate"])

    assert result.exit_code == 1
    assert "unknown action" in result.output
    assert "teleport" in result.output


def test_journey_validate_rejects_unsupported_target(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    specs = _make_specs(tmp_path)
    _write_journey(specs, target="desktop")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["journey", "validate"])

    assert result.exit_code == 1
    assert "journey_target_unsupported" in result.output
    assert "desktop" in result.output


def test_wait_without_until_or_reason_is_warning(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Fixed waits without a reason remain valid but are reported as warnings."""
    specs = _make_specs(tmp_path)
    journey = _write_journey(specs)
    journey.write_text(
        journey.read_text(encoding="utf-8").replace(
            '- wait: { seconds: 10, until: { text: "Dashboard" } }',
            "- wait: { seconds: 10 }",
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["journey", "validate"])

    assert result.exit_code == 0, result.output
    assert "warnings=1" in result.output
    assert "wait_reason_missing" in result.output


def test_manual_journey_requires_reason(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    specs = _make_specs(tmp_path)
    _write_journey(
        specs,
        journey_id="manual",
        extra="run_policy: manual\n",
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["journey", "validate"])

    assert result.exit_code == 1
    assert "journey_manual_reason_missing" in result.output


def test_compile_generates_playwright_with_source_hash(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Web journeys compile ahead-of-time to deterministic Playwright tests."""
    specs = _make_specs(tmp_path)
    _write_journey(specs)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["journey", "compile", "--feature", "012-auth"])

    artifact = tmp_path / "tests" / "e2e" / "journeys" / "012-auth" / "login_happy_path.spec.ts"
    assert result.exit_code == 0, result.output
    assert artifact.exists()
    text = artifact.read_text(encoding="utf-8")
    assert "livespec-journey-source-hash:" in text
    assert 'page.waitForSelector("text=Dashboard", { timeout: 10000 })' in text


def test_compile_generates_xcuitest_for_ios_and_watchos(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Apple surfaces compile to Swift UI test artifacts."""
    specs = _make_specs(tmp_path)
    _write_journey(specs, journey_id="ios-login", target="ios")
    _write_journey(specs, journey_id="watch-login", target="watchos")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["journey", "compile", "--feature", "012-auth"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "STRAPTUITests" / "Journeys" / "IosLoginJourney.swift").exists()
    assert (tmp_path / "STRAPTUITests" / "Journeys" / "WatchLoginJourney.swift").exists()


def test_doctor_reports_stale_and_removed_ac(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Doctor catches stale compiled artifacts and removed AC coverage."""
    specs = _make_specs(tmp_path)
    journey = _write_journey(specs)
    monkeypatch.chdir(tmp_path)
    compile_result = runner.invoke(app, ["journey", "compile", "--feature", "012-auth"])
    assert compile_result.exit_code == 0, compile_result.output
    journey.write_text(
        journey.read_text(encoding="utf-8").replace("AC-002", "AC-999"),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["doctor", "--format", "json"])

    assert result.exit_code == 1
    report = json.loads(result.output)
    codes = {finding["code"] for finding in report["findings"]}
    assert "journey_compiled_stale" in codes
    assert "journey_requirement_missing" in codes


def test_manual_disabled_and_executable_categories_are_reported(
    tmp_path: Path,
) -> None:
    """Journey scanning keeps executable, manual, and disabled categories distinct."""
    specs = _make_specs(tmp_path)
    _write_journey(specs, journey_id="executable", target="web")
    _write_journey(
        specs,
        journey_id="manual",
        target="web",
        extra='run_policy: manual\nmanual_reason: "Requires hardware token"\n',
    )
    _write_journey(specs, journey_id="disabled", target="web", extra="disabled: true\n")

    report = scan_journeys(tmp_path, feature="012-auth")

    assert report.executable_count == 1
    assert report.manual_count == 1
    assert report.disabled_count == 1
