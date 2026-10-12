# LiveSpec traceability anchors
# @spec(AC-006)
# @spec(AC-007)
# @spec(AC-013)
# @spec(FR-005)
# @spec(FR-007)

"""`select` support and XCUITest destination resolution (Feature 056)."""

# @spec FR-005: select on Playwright only
# — .specs/features/056-executable-user-journeys/spec.md#fr-005
# @spec FR-007: XCUITest target from the project
# — .specs/features/056-executable-user-journeys/spec.md#fr-007

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.test_journeys_wait_manual import write_journey
from validator.cli import app

runner = CliRunner()
SELECT = '  - action: select\n    target: { label: "Plan" }\n    value: "pro"\n'
SWIFT = "Journeys/LoginFlowJourney.swift"


def _compile(root: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[int, str]:
    monkeypatch.chdir(root)
    result = runner.invoke(app, ["journey", "compile", "--journey", "login-flow"])
    return result.exit_code, result.output


class TestSelect:
    def test_playwright_compiles_select_option(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_journey(tmp_path, steps=SELECT)
        code, output = _compile(tmp_path, monkeypatch)
        assert code == 0, output
        text = (tmp_path / "tests/e2e/journeys/login_flow.spec.ts").read_text(encoding="utf-8")
        assert "await page.getByText('Plan').selectOption('pro');" in text

    @pytest.mark.parametrize(
        ("runner_name", "surface"), [("xcuitest", "ios"), ("maestro", "android")]
    )
    def test_other_runners_refuse_select(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, runner_name: str, surface: str
    ) -> None:
        (tmp_path / "AppUITests").mkdir()
        write_journey(tmp_path, steps=SELECT, runner_name=runner_name, surface=surface)
        code, output = _compile(tmp_path, monkeypatch)
        assert code == 1
        assert "journey_capability_unsupported" in output
        assert "'select'" in output
        assert not (tmp_path / "AppUITests" / SWIFT).exists()


class TestXcuitestDestination:
    def test_unique_ios_target_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "ShopUITests").mkdir()
        (tmp_path / "ShopWatchUITests").mkdir()
        write_journey(tmp_path, runner_name="xcuitest", surface="ios")
        code, output = _compile(tmp_path, monkeypatch)
        assert code == 0, output
        assert (tmp_path / "ShopUITests" / SWIFT).exists()
        assert not (tmp_path / "STRAPTUITests").exists()

    def test_watchos_uses_watch_target(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "ShopUITests").mkdir()
        (tmp_path / "ShopWatchUITests").mkdir()
        write_journey(tmp_path, runner_name="xcuitest", surface="watchos")
        code, output = _compile(tmp_path, monkeypatch)
        assert code == 0, output
        assert (tmp_path / "ShopWatchUITests" / SWIFT).exists()

    def test_watchos_without_watch_target_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "ShopUITests").mkdir()
        write_journey(tmp_path, runner_name="xcuitest", surface="watchos")
        code, output = _compile(tmp_path, monkeypatch)
        assert code == 3
        assert "journey_xcuitest_target_unresolved" in output
        assert "watchos" in output

    def test_several_ios_targets_are_ambiguous(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "AlphaUITests").mkdir()
        (tmp_path / "BetaUITests").mkdir()
        write_journey(tmp_path, runner_name="xcuitest", surface="ios")
        code, output = _compile(tmp_path, monkeypatch)
        assert code == 3
        assert "AlphaUITests" in output
        assert "BetaUITests" in output
        assert "testDir" in output

    def test_no_target_directory_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_journey(tmp_path, runner_name="xcuitest", surface="ios")
        code, output = _compile(tmp_path, monkeypatch)
        assert code == 3
        assert "journey_xcuitest_target_unresolved" in output

    def test_surfaces_test_dir_overrides(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "AlphaUITests").mkdir()
        (tmp_path / "BetaUITests").mkdir()
        write_journey(tmp_path, runner_name="xcuitest", surface="ios")
        (tmp_path / ".specs" / "surfaces.yaml").write_text(
            "surfaces:\n  - id: ios\n    runner: xcuitest\n    platform: ios\n"
            "    testDir: apps/ios/BetaUITests\n",
            encoding="utf-8",
        )
        code, output = _compile(tmp_path, monkeypatch)
        assert code == 0, output
        assert (tmp_path / "apps/ios/BetaUITests" / SWIFT).exists()
