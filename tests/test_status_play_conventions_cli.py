"""Tests for deterministic utility command backends."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from validator.cli import app

runner = CliRunner()


def test_status_outputs_json_without_mutating_project(
    monkeypatch: object, tmp_path: Path
) -> None:
    specs = tmp_path / ".specs"
    feature_dir = specs / "features" / "001-demo"
    feature_dir.mkdir(parents=True)
    (specs / "roadmap.md").write_text(
        "## MVP\n<!-- roadmap:mvp:start -->\n- [ ] **Demo** — Scope: S\n<!-- roadmap:mvp:end -->\n",
        encoding="utf-8",
    )
    (feature_dir / "spec.md").write_text(
        "---\ntitle: Demo\nstatus: Draft\ncreated: 2026-05-18\n---\n# Demo\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["status", "--repo", str(tmp_path), "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["features"]["total"] == 1
    assert payload["roadmap"]["mvp"]["open"] == 1
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")) == [
        ".specs",
        ".specs/features",
        ".specs/features/001-demo",
        ".specs/features/001-demo/spec.md",
        ".specs/roadmap.md",
    ]


def test_play_coverage_writes_data_json_without_opening_browser(tmp_path: Path) -> None:
    (tmp_path / ".specs").mkdir()
    source = tmp_path / "src"
    source.mkdir()
    (source / "feature.py").write_text(
        "# @spec FR-001: Demo — .specs/features/001-demo/spec.md#fr-001\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "play-coverage",
            "--repo",
            str(tmp_path),
            "--source-dir",
            str(source),
            "--feature",
            "001-demo",
            "--no-open",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["anchor_count"] == 1
    assert (tmp_path / "playground" / "coverage" / "data.json").is_file()


def test_conventions_refresh_generates_index_and_manifest(tmp_path: Path) -> None:
    stacks = tmp_path / ".specs" / "stacks"
    stacks.mkdir(parents=True)
    (stacks / "_default.md").write_text(
        "# Stack\n\n- Python\n- CLI\n", encoding="utf-8"
    )

    result = runner.invoke(app, ["conventions", "refresh", "--repo", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "conventions" in result.output
    assert (tmp_path / ".conventions" / "index.md").is_file()
    assert (tmp_path / ".conventions" / "manifest.yaml").is_file()
