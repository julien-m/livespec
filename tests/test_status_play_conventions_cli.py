# LiveSpec traceability anchors
# @spec(AC-009)
# @spec(AC-010)

"""Tests for deterministic utility command backends."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from validator.cli import app
from validator.conventions_gate import GateResult, GateVerdict

runner = CliRunner()


def test_status_outputs_json_without_mutating_project(monkeypatch: object, tmp_path: Path) -> None:
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
    (stacks / "_default.md").write_text("# Stack\n\n- Python\n- CLI\n", encoding="utf-8")

    result = runner.invoke(app, ["conventions", "refresh", "--repo", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "conventions" in result.output
    assert (tmp_path / ".conventions" / "index.md").is_file()
    assert (tmp_path / ".conventions" / "manifest.yaml").is_file()


def test_conventions_refresh_generates_web_design_domains(tmp_path: Path) -> None:
    stacks = tmp_path / ".specs" / "stacks"
    stacks.mkdir(parents=True)
    (stacks / "_default.md").write_text(
        "# Stack\n\n- React\n- Vite\n- Web dashboard\n", encoding="utf-8"
    )

    result = runner.invoke(app, ["conventions", "refresh", "--repo", str(tmp_path)])

    assert result.exit_code == 0, result.output
    index = (tmp_path / ".conventions" / "index.md").read_text(encoding="utf-8")
    manifest = (tmp_path / ".conventions" / "manifest.yaml").read_text(encoding="utf-8")
    for domain in (
        "design-tokens",
        "design-components",
        "design-views",
        "design-quality",
    ):
        assert f"## {domain}" in index
        assert f"- name: {domain}" in manifest


def test_conventions_supervisor_gate_blocks_protected_diff(tmp_path: Path) -> None:
    repo = _init_conventions_git_repo(tmp_path)
    (repo / ".specs" / "conventions-gates.yaml").write_text(
        _gates_yaml(repo, exclusions=[".venv/**"]),
        encoding="utf-8",
    )
    _git(repo, "add", ".specs/conventions-gates.yaml")
    _git(repo, "commit", "-m", "change gates")

    result = runner.invoke(
        app,
        [
            "conventions",
            "supervisor-gate",
            "--repo",
            str(repo),
            "--base-ref",
            "HEAD~1",
            "--head-ref",
            "HEAD",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "BLOCKED"
    assert payload["reason"] == "gate_files_modified_in_pipeline"
    assert ".specs/conventions-gates.yaml" in payload["protected_paths"]


def test_conventions_supervisor_gate_blocks_current_hash_mismatch(tmp_path: Path) -> None:
    repo = _init_conventions_git_repo(tmp_path)
    (repo / ".specs" / "conventions-rulebook.yaml").write_text(
        "schema_version: 1\ncompiled_at: changed\nsources: []\nrules: []\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "conventions",
            "supervisor-gate",
            "--repo",
            str(repo),
            "--base-ref",
            "HEAD",
            "--head-ref",
            "HEAD",
            "--json",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "BLOCKED"
    assert payload["reason"] == "base_hash_mismatch"
    assert payload["blockers"] == ["rules_sha256_mismatch"]


def test_conventions_supervisor_gate_uses_fresh_verification(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    repo = _init_conventions_git_repo(tmp_path)

    def fail_fresh_verification(project_root: Path, *, report: bool = False) -> GateResult:
        assert project_root == repo.resolve()
        return GateResult(verdict=GateVerdict.FAIL, violations=[], blockers=[])

    monkeypatch.setattr(
        "validator.cli_commands.utility_cmd.verify_conventions",
        fail_fresh_verification,
    )
    result = runner.invoke(
        app,
        [
            "conventions",
            "supervisor-gate",
            "--repo",
            str(repo),
            "--base-ref",
            "HEAD",
            "--head-ref",
            "HEAD",
            "--json",
        ],
    )

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["verdict"] == "FAIL"
    assert payload["source"] == "fresh_supervisor_run"


def _init_conventions_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    (repo / ".specs").mkdir()
    (repo / ".specs" / "constitution.md").write_text("ruff limits\n", encoding="utf-8")
    (repo / ".specs" / "conventions-gates.yaml").write_text(_gates_yaml(repo), encoding="utf-8")
    (repo / ".specs" / "conventions-rulebook.yaml").write_text(
        "schema_version: 1\ncompiled_at: now\nsources: []\nrules: []\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".specs")
    _git(repo, "commit", "-m", "base")
    return repo


def _gates_yaml(repo: Path, *, exclusions: list[str] | None = None) -> str:
    from validator.visual_evidence import sha256_file

    exclusion_lines = "\n".join(f"  - {item}" for item in exclusions or [])
    return f"""\
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: {sha256_file(repo / ".specs" / "constitution.md")}
  stack: .specs/stacks/_default.md
commands: {{}}
builtin: {{}}
coverage: {{}}
exclusions:
{exclusion_lines}
scope: repo
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=LiveSpec Test",
            "-c",
            "user.email=livespec@example.test",
            *args,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
