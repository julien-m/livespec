"""Preparation contracts must not demand post-implementation work.

@spec(FR-015) @spec(AC-014) — 078-requirement-evidence-integrity
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.goal_contracts import compile_command_goal
from validator.verify_output import evaluate_rules

REPO_ROOT = Path(__file__).resolve().parents[1]
FEATURE = "001-example"


def _project(tmp_path: Path, *, visual: bool = False) -> Path:
    feature = tmp_path / ".specs" / "features" / FEATURE
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text(
        "# Feature\n\n## Functional Requirements\n- FR-001: Export CSV.\n"
        + ("\n## Screens\n- Export screen.\n" if visual else ""),
        encoding="utf-8",
    )
    (feature / "plan.md").write_text("# Plan\nImplement FR-001.\n", encoding="utf-8")
    (tmp_path / ".specs" / "constitution.md").write_text(
        "# Constitution\nKeep it simple.\n", encoding="utf-8"
    )
    if visual:
        (tmp_path / "penflow").mkdir()
    return feature


@pytest.mark.parametrize("visual", [False, True])
@pytest.mark.parametrize(
    "flags", ["--pre-impl", "--pre-impl --fix --all --quality --visual-status"]
)
def test_preparation_contract_excludes_post_implementation_tasks(
    tmp_path: Path, visual: bool, flags: str
) -> None:
    _project(tmp_path, visual=visual)
    goal = compile_command_goal(
        "spec-check", project_root=tmp_path, livespec_root=REPO_ROOT, feature=FEATURE, flags=flags
    )
    tasks = [task["description"] for task in goal.payload["tasks"]]
    forbidden = (
        "Read implementation map from",
        "Verify each FR/AC against actual code",
        "Save gap report",
        "Add check entry",
        "Add summary entry",
        "Capture fresh runtime",
        "visual-gate certify",
        "--required-profile implementation",
        "Spawn independent native sub-agent",
        "implementation.md status values refreshed",
        "Gap report saved",
        "has a check entry",
        "has a summary entry",
    )
    assert not any(fragment in task for fragment in forbidden for task in tasks)
    assert any("Run `livespec validate --pre-impl" in task for task in tasks)
    assert any("absent implementation map is accepted" in task for task in tasks)
    assert any("readiness only" in task for task in tasks) is visual
    assert len(goal.payload["definition_of_done"]) == 2
    assert goal.payload["verify_rules"]["when"][0]["must"] == [
        {"verb": "must", "kind": "contains", "payload": "Specification Analysis Report"}
    ]


def test_default_full_check_keeps_implementation_and_visual_proof(tmp_path: Path) -> None:
    _project(tmp_path, visual=True)
    goal = compile_command_goal(
        "spec-check", project_root=tmp_path, livespec_root=REPO_ROOT, feature=FEATURE
    )
    tasks = [task["description"] for task in goal.payload["tasks"]]
    for required in (
        "Read implementation map from",
        "Verify each FR/AC against actual code",
        "Save gap report",
        "Add check entry",
        "Add summary entry",
        "--required-profile implementation",
        "visual-gate certify",
    ):
        assert any(required in task for task in tasks), required
    assert not any("Run `livespec validate --pre-impl" in task for task in tasks)


def test_preparation_cli_matches_contract_without_implementation_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    feature = _project(tmp_path)
    monkeypatch.chdir(tmp_path)
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = CliRunner().invoke(
        app,
        ["validate", "--pre-impl", "--structural-only", "--format", "json", str(feature)],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["metrics"]["implementation_present"] == 0
    assert data["metrics"]["coverage_percent"] == 100.0
    markdown = CliRunner().invoke(
        app, ["validate", "--pre-impl", str(feature)], catch_exceptions=False
    )
    goal = compile_command_goal(
        "spec-check",
        project_root=tmp_path,
        livespec_root=REPO_ROOT,
        feature=FEATURE,
        flags="--pre-impl",
    )
    report = evaluate_rules(
        goal.payload["verify_rules"],
        artifact={"exit_code": markdown.exit_code, "stdout": markdown.output},
        active_flags=goal.payload["normalized_flags"],
        feature=FEATURE,
        project_root=tmp_path,
    )
    assert report.outcome == "success"
    assert [rule.status for rule in report.rules] == ["PASS"]
    assert {
        p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    } == before
