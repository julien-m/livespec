# LiveSpec traceability anchors
# @spec(AC-002)

"""Feature-scoped ``livespec test --feature`` selection (Feature 035, AC-002)."""

# @spec AC-002: Feature-scoped test selection
# — .specs/features/035-unified-cli-surface/spec.md#ac-002

from __future__ import annotations

from pathlib import Path
from typing import Literal
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.cli_resolvers import resolve_feature_dir
from validator.drivers.registry import DriverRegistry
from validator.drivers.runner import run_capability
from validator.drivers.schemas import CapabilityResult, DetectRule, DriverCapability, DriverManifest
from validator.exceptions import DriverTestSelectionError, FeatureResolutionError

runner = CliRunner()


def _project(root: Path, *features: str) -> Path:
    specs = root / ".specs"
    for feature in features:
        (specs / "features" / feature).mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    return specs


def _map_tests(specs: Path, feature: str, *test_files: str) -> None:
    rows = "\n".join(f"| AC-00{i} | `{name}` | ✅ |" for i, name in enumerate(test_files, 1))
    (specs / "features" / feature / "implementation.md").write_text(
        f"## Acceptance Criteria Mapping\n\n| AC | Test File | Status |\n|---|---|---|\n{rows}\n",
        encoding="utf-8",
    )


class TestResolveFeatureDir:
    def test_number_does_not_match_sub_feature(self, tmp_path: Path) -> None:
        _project(tmp_path, "005-ui", "005.1-audit")
        assert resolve_feature_dir(tmp_path, "005").name == "005-ui"

    def test_exact_directory_name(self, tmp_path: Path) -> None:
        _project(tmp_path, "005-ui", "005.1-audit")
        assert resolve_feature_dir(tmp_path, "005.1-audit").name == "005.1-audit"

    def test_zero_matches_lists_nothing(self, tmp_path: Path) -> None:
        _project(tmp_path, "005-ui")
        with pytest.raises(FeatureResolutionError, match="999"):
            resolve_feature_dir(tmp_path, "999")

    def test_several_matches_are_listed(self, tmp_path: Path) -> None:
        _project(tmp_path, "007-alpha", "007-beta")
        with pytest.raises(FeatureResolutionError, match=r"007-alpha.*007-beta"):
            resolve_feature_dir(tmp_path, "007")


class TestRunCapabilitySelection:
    def _driver(self, selection: Literal["append"] | None) -> DriverManifest:
        return DriverManifest(
            name="fake",
            detect=DetectRule(files=["pyproject.toml"]),
            coverage=DriverCapability(
                command="python -c pass",
                report_path="lcov.info",
                test_selection=selection,
            ),
        )

    def test_append_adds_paths_after_command(self, tmp_path: Path) -> None:
        with patch("validator.drivers.runner.run_owned", return_value=(0, "", "")) as run_mock:
            run_capability(
                self._driver("append"),
                "coverage",
                project_root=tmp_path,
                test_paths=["tests/test_a.py", "tests/test_b.py"],
            )
        argv = run_mock.call_args.args[0]
        assert argv == ["python", "-c", "pass", "tests/test_a.py", "tests/test_b.py"]

    def test_without_declaration_refuses(self, tmp_path: Path) -> None:
        with pytest.raises(DriverTestSelectionError):
            run_capability(
                self._driver(None), "coverage", project_root=tmp_path, test_paths=["t.py"]
            )

    @staticmethod
    def _builtins(tmp_path: Path) -> list[DriverManifest]:
        registry = DriverRegistry(tmp_path)
        registry.discover()
        return registry.all()

    def test_legacy_manifest_without_field_still_loads(self, tmp_path: Path) -> None:
        names = {driver.name for driver in self._builtins(tmp_path)}
        assert {"python", "go", "rust"} <= names

    def test_builtin_python_declares_append(self, tmp_path: Path) -> None:
        python = next(d for d in self._builtins(tmp_path) if d.name == "python")
        assert python.coverage is not None
        assert python.coverage.test_selection == "append"


class TestTestCommandFeature:
    def test_selected_tests_are_passed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        specs = _project(tmp_path, "035-cli", "035.1-extra")
        _map_tests(specs, "035-cli", "tests/test_cli_unified.py")
        monkeypatch.chdir(tmp_path)
        captured: dict[str, object] = {}

        def _fake(driver: object, capability: str, **kwargs: object) -> CapabilityResult:
            captured.update(kwargs)
            return CapabilityResult(
                capability_name=capability, exit_code=0, report_path=None, stdout="", stderr=""
            )

        with patch("validator.cli_commands.test_selection.run_capability", side_effect=_fake):
            result = runner.invoke(app, ["test", "--feature", "035"])
        assert result.exit_code == 0, result.output
        assert captured["test_paths"] == ["tests/test_cli_unified.py"]
        assert captured["feature"] == "035-cli"

    def test_unresolvable_feature_exits_2(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _project(tmp_path, "035-cli")
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["test", "--feature", "999"])
        assert result.exit_code == 2, result.output

    def test_driver_without_selection_exits_3(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        specs = _project(tmp_path, "035-cli")
        _map_tests(specs, "035-cli", "tests/test_cli_unified.py")
        monkeypatch.chdir(tmp_path)
        bare = DriverManifest(
            name="go",
            detect=DetectRule(files=["pyproject.toml"]),
            coverage=DriverCapability(command="go test ./...", report_path="lcov.info"),
        )
        with patch("validator.cli_commands.test_cmd.resolve_primary_driver", return_value=bare):
            result = runner.invoke(app, ["test", "--feature", "035"])
        assert result.exit_code == 3, result.output
        assert "test_selection" in result.output

    def test_feature_without_selected_tests_exits_3(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _project(tmp_path, "035-cli")
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["test", "--feature", "035"])
        assert result.exit_code == 3, result.output
