# LiveSpec traceability anchors
# @spec(AC-003)
# @spec(AC-004)
# @spec(AC-015)

"""Journey `wait` semantics and manual reasons on the v2 path (Feature 056)."""

# @spec AC-003: Bounded conditional wait
# — .specs/features/056-executable-user-journeys/spec.md#ac-003
# @spec AC-004: Fixed wait warning — .specs/features/056-executable-user-journeys/spec.md#ac-004
# @spec AC-015: Manual journeys need a reason
# — .specs/features/056-executable-user-journeys/spec.md#ac-015

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.journeys import scan_journeys
from validator.journeys.runner import run_journeys

runner = CliRunner()

LOGIN_STEPS = """  - action: open
    target: { route: "ROUTE" }
  - action: click
    target: { text: "Login", product_contract: true }
"""


def write_journey(
    root: Path,
    *,
    steps: str = "",
    runner_name: str = "playwright",
    surface: str = "web",
    status: str = "active",
    policy: str = "always",
    header: str = "",
    journey_id: str = "login-flow",
) -> Path:
    """Write a feature spec plus one v2 journey and return the journey source path."""
    feature_dir = root / ".specs" / "features" / "012-auth"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        "# Auth\n\n## Acceptance Criteria\n\n- **AC-001:** Login works.\n", encoding="utf-8"
    )
    journey_dir = root / ".specs" / "journeys" / journey_id
    journey_dir.mkdir(parents=True, exist_ok=True)
    route = "myapp://login" if runner_name == "xcuitest" else "/login"
    source = journey_dir / "journey.yaml"
    source.write_text(
        f"""schema_version: 2
id: {journey_id}
title: Login flow
status: {status}
description: User logs in.
{header}covers:
  - feature: 012-auth
    kind: ac
    ref: AC-001
    reason: Login works.
run_policy:
  local: {policy}
targets:
  - surface: {surface}
    runner: {runner_name}
steps:
{LOGIN_STEPS.replace("ROUTE", route)}{steps}privacy:
  llm_allowed: false
  retention: none
""",
        encoding="utf-8",
    )
    (journey_dir / "changelog.md").write_text("# Changelog\n", encoding="utf-8")
    return source


UNTIL = (
    '  - action: wait\n    seconds: 10\n    until: { text: "Dashboard", product_contract: true }\n'
)


class TestFixedWaitWarning:
    """AC-004."""

    def test_fixed_wait_without_until_or_reason_warns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_journey(tmp_path, steps="  - action: wait\n    seconds: 3\n")
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["journey", "validate"])
        assert result.exit_code == 0, result.output
        assert "WARNING wait_reason_missing" in result.output
        assert "wait.seconds at step 3 needs until or reason" in result.output
        assert "warnings=1" in result.output

    @pytest.mark.parametrize(
        "wait_step",
        [
            '  - action: wait\n    seconds: 3\n    reason: "Animation settles"\n',
            UNTIL,
        ],
    )
    def test_reason_or_until_silences_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wait_step: str
    ) -> None:
        write_journey(tmp_path, steps=wait_step)
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["journey", "validate"])
        assert result.exit_code == 0, result.output
        assert "wait_reason_missing" not in result.output

    def test_blank_reason_still_warns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_journey(tmp_path, steps='  - action: wait\n    seconds: 3\n    reason: "  "\n')
        monkeypatch.chdir(tmp_path)
        assert "wait_reason_missing" in runner.invoke(app, ["journey", "validate"]).output

    @pytest.mark.parametrize(
        "bad_step",
        [
            '  - action: wait\n    until: { text: "Dashboard", product_contract: true }\n',
            '  - action: click\n    target: { label: "Go" }\n    until: { label: "Done" }\n',
        ],
    )
    def test_malformed_wait_is_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_step: str
    ) -> None:
        write_journey(tmp_path, steps=bad_step)
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["journey", "validate"])
        assert result.exit_code == 1
        assert "journey_schema_invalid" in result.output


class TestBoundedWaitCompilation:
    """AC-003."""

    def _compile(self, root: Path, monkeypatch: pytest.MonkeyPatch, **kwargs: str) -> str:
        monkeypatch.chdir(root)
        result = runner.invoke(app, ["journey", "compile", "--journey", "login-flow"])
        assert result.exit_code == 0, result.output
        return result.output

    def test_playwright_until(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        write_journey(tmp_path, steps=UNTIL)
        self._compile(tmp_path, monkeypatch)
        text = (tmp_path / "tests/e2e/journeys/login_flow.spec.ts").read_text(encoding="utf-8")
        assert "await expect(page.getByText('Dashboard')).toBeVisible({ timeout: 10000 });" in text

    def test_playwright_fixed_delay(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        write_journey(tmp_path, steps='  - action: wait\n    seconds: 2\n    reason: "Toast"\n')
        self._compile(tmp_path, monkeypatch)
        text = (tmp_path / "tests/e2e/journeys/login_flow.spec.ts").read_text(encoding="utf-8")
        assert "await page.waitForTimeout(2000);" in text

    def test_xcuitest_until_waits_for_hittable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "AppUITests").mkdir()
        write_journey(tmp_path, steps=UNTIL, runner_name="xcuitest", surface="ios")
        self._compile(tmp_path, monkeypatch)
        text = (tmp_path / "AppUITests/Journeys/LoginFlowJourney.swift").read_text(encoding="utf-8")
        assert 'NSPredicate(format: "exists == true AND hittable == true")' in text
        assert "timeout: 10" in text
        assert ".completed" in text

    def test_maestro_until(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        write_journey(tmp_path, steps=UNTIL, runner_name="maestro", surface="android")
        self._compile(tmp_path, monkeypatch)
        text = (tmp_path / ".specs/maestro/journeys/login_flow.yaml").read_text(encoding="utf-8")
        assert "extendedWaitUntil:" in text
        assert "visible: Dashboard" in text
        assert "timeout: 10000" in text

    def test_maestro_fixed_wait_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_journey(
            tmp_path,
            steps='  - action: wait\n    seconds: 2\n    reason: "Toast"\n',
            runner_name="maestro",
            surface="android",
        )
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["journey", "compile", "--journey", "login-flow"])
        assert result.exit_code == 1
        assert "journey_capability_unsupported" in result.output
        assert not (tmp_path / ".specs/maestro/journeys/login_flow.yaml").exists()


class TestManualReason:
    """AC-015."""

    @pytest.mark.parametrize(("status", "policy"), [("manual", "always"), ("active", "manual")])
    def test_manual_without_reason_fails_validation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str, policy: str
    ) -> None:
        write_journey(tmp_path, status=status, policy=policy)
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["journey", "validate"])
        assert result.exit_code == 1
        assert "ERROR journey_manual_reason_missing" in result.output
        assert "manual journeys require manual_reason" in result.output
        assert scan_journeys(tmp_path).manual_count == 0

    def test_run_reports_missing_reason_instead_of_skipping(self, tmp_path: Path) -> None:
        write_journey(tmp_path, policy="manual")
        result = run_journeys(tmp_path, journey="login-flow", execute=False)
        assert result.manual == []
        assert [issue.code for issue in result.issues] == ["journey_manual_reason_missing"]

    def test_manual_with_reason_is_reported_as_manual(self, tmp_path: Path) -> None:
        write_journey(
            tmp_path, policy="manual", header='manual_reason: "Needs a physical card reader"\n'
        )
        report = scan_journeys(tmp_path)
        assert report.manual_count == 1
        manual = [f for f in report.findings if f.code == "journey_manual"]
        assert "Needs a physical card reader" in manual[0].message
        assert run_journeys(tmp_path, journey="login-flow", execute=False).manual == ["login-flow"]


def test_v1_migration_keeps_manual_reason(tmp_path: Path) -> None:
    """AC-015: migrating a manual v1 journey keeps its reason, so it stays valid."""
    from validator.journeys.migration import migrate_v1_journeys

    feature_dir = tmp_path / ".specs" / "features" / "012-auth"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("- **AC-001:** Login works.\n", encoding="utf-8")
    legacy_dir = tmp_path / ".specs" / "journeys" / "012-auth"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "card-reader.journey.yaml").write_text(
        "id: card-reader\nfeature: 012-auth\ntitle: Card reader\nrun_policy: manual\n"
        "manual_reason: Needs a physical card reader\ncovers:\n  ac: [AC-001]\n",
        encoding="utf-8",
    )
    migrate_v1_journeys(tmp_path, apply=True)
    migrated = (tmp_path / ".specs/journeys/card-reader/journey.yaml").read_text(encoding="utf-8")
    assert "manual_reason: Needs a physical card reader" in migrated
