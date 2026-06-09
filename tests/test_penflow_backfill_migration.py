# LiveSpec traceability anchors
# @spec(AC-009)
# @spec(AC-010)
# @spec(AC-011)
# @spec(AC-012)
# @spec(AC-013)

"""Tests for Migration 17 Penflow backfill behavior."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATE_SH = REPO_ROOT / "scripts" / "migrate.sh"
MIGRATION_17 = REPO_ROOT / "migrations" / "17" / "migrate.md"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _project(root: Path, version: int = 16) -> Path:
    (root / ".specs").mkdir(parents=True)
    (root / ".specs" / "livespec-version").write_text(f"{version}\n", encoding="utf-8")
    return root


def _complete_penflow(root: Path) -> None:
    (root / "penflow" / "flow-ui-contract").mkdir(parents=True)
    _write_json(root / "penflow" / "ui.pen", {"children": [{"type": "frame"}]})
    _write_json(root / "penflow" / "semantic-ui-tree.json", {"flows": [], "screens": []})
    _write_json(root / "penflow" / "expected-ui-tree.json", {"screens": []})
    _write_json(root / "penflow" / "code-ir.json", {"flows": []})


def _run_migration(project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(MIGRATE_SH), str(MIGRATION_17), str(project), str(REPO_ROOT)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_penflow_backfill_noops_when_workspace_complete(tmp_path: Path) -> None:
    project = _project(tmp_path / "project")
    _complete_penflow(project)
    original_ui_pen = (project / "penflow" / "ui.pen").read_text(encoding="utf-8")

    result = _run_migration(project)

    assert result.returncode == 0, result.stderr
    assert (project / ".specs" / "livespec-version").read_text().strip() == "17"
    assert (project / "penflow" / "ui.pen").read_text(encoding="utf-8") == original_ui_pen
    report = (project / ".specs" / "migrations" / "017-penflow-backfill-report.md").read_text(
        encoding="utf-8"
    )
    assert "Verdict: PASS" in report
    assert "preserved existing complete root penflow workspace" in report


def test_penflow_backfill_blocks_absent_runtime_without_fake_penflow(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path / "project")
    (project / ".specs" / "design" / "screens").mkdir(parents=True)
    (project / ".specs" / "design" / "screens" / "legacy.png").write_bytes(b"png")

    result = _run_migration(project)

    assert result.returncode == 0, result.stderr
    assert not (project / "penflow" / "ui.pen").exists()
    report = (project / ".specs" / "migrations" / "017-penflow-backfill-report.md").read_text(
        encoding="utf-8"
    )
    assert "Verdict: BLOCKED" in report
    assert "runtime UI source not detected" in report


def test_penflow_backfill_reports_legacy_design_ui_pen_without_promoting_it(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path / "project")
    legacy_pen = project / ".specs" / "design" / "ui.pen"
    legacy_pen.parent.mkdir(parents=True)
    legacy_pen.write_text("legacy", encoding="utf-8")

    result = _run_migration(project)

    assert result.returncode == 0, result.stderr
    assert legacy_pen.exists()
    assert not (project / "penflow" / "ui.pen").exists()
    report = (project / ".specs" / "migrations" / "017-penflow-backfill-report.md").read_text(
        encoding="utf-8"
    )
    assert ".specs/design/ui.pen" in report
    assert "non-canonical legacy evidence" in report


def test_penflow_backfill_creates_no_secondary_pen_files(tmp_path: Path) -> None:
    project = _project(tmp_path / "project")

    result = _run_migration(project)

    assert result.returncode == 0, result.stderr
    pen_files = sorted(path.relative_to(project).as_posix() for path in project.rglob("*.pen"))
    assert pen_files == []
