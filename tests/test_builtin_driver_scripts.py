"""Built-in driver scripts resolve beside their shipped manifest (016 FR-003, AC-010)."""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.drivers.registry import DriverRegistry
from validator.drivers.runner import run_capability


def test_builtin_script_capability_runs_shipped_script_in_any_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "go.mod").write_text("module example.com/demo\n")
    driver = next(m for m in DriverRegistry(tmp_path).discover() if m.name == "go")
    launched: list[list[str]] = []

    def fake_run(argv: list[str], _root: Path, _env: dict[str, str]) -> tuple[int, str, str]:
        launched.append(argv)
        return 127, "", "not executed: inspect the owned-process boundary"

    monkeypatch.setattr("validator.drivers.runner.run_owned", fake_run)

    run_capability(driver, "coverage", project_root=tmp_path)

    assert driver.source_path is not None
    shipped = driver.source_path.parent / "scripts" / "go-coverage-gate.sh"
    assert launched == [["bash", str(shipped)]]


def test_custom_driver_script_still_resolves_against_project_root(tmp_path: Path) -> None:
    drivers = tmp_path / ".specs" / "drivers"
    drivers.mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "cov.sh").write_text("echo ok\n")
    (tmp_path / "marker.custom").write_text("")
    (drivers / "custom.yaml").write_text(
        "name: custom\ndetect:\n  files: [marker.custom]\n"
        "coverage:\n  script: scripts/cov.sh\n  report_path: cov.info\n"
    )
    driver = next(m for m in DriverRegistry(tmp_path).discover() if m.name == "custom")

    result = run_capability(driver, "coverage", project_root=tmp_path)

    assert "ok" in result.stdout
