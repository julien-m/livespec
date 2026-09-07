"""Rendered preview goals omit business writes and cannot prove execution with prose."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.evidence_policy import typed_evidence_missing
from validator.goal_contracts import (
    GoalContract,
    compile_command_goal,
    render_goal_contract_file,
    render_goal_state_file,
)

ROOT = Path(__file__).parents[1]
REPORT_WRITES = (
    "Save report to",
    "Update implementation.md",
    "Add entry to feature changelog.md",
    "Add summary line to",
    "Test report saved",
    "`implementation.md` AC status updated",
    "Feature `changelog.md` has test entry",
    "Global `.specs/changelog.md` has summary entry",
)


def _goal(root: Path, command: str, flags: str, visual: bool) -> GoalContract:
    feature = root / ".specs/features/001-screen"
    feature.mkdir(parents=True)
    text = "# Screen\n## Acceptance Criteria\n### AC-001\nScreen shown.\n"
    if visual:
        text += "## Screens\nMain screen.\n"
        (root / "penflow").mkdir()
    (feature / "spec.md").write_text(text)
    return compile_command_goal(
        command,
        project_root=root,
        livespec_root=ROOT,
        feature=None if "--all" in flags else feature.name,
        flags=flags,
    )


@pytest.mark.parametrize("visual", [False, True])
@pytest.mark.parametrize(
    "flags", ["--dry-run", "-d", "--audit-only", "--conventions --dry-run", "--all --dry-run"]
)
def test_fix_preview_cannot_require_report_generation_or_conventions_refresh(
    tmp_path: Path, flags: str, visual: bool
) -> None:
    goal = _goal(tmp_path, "spec-fix", flags, visual)
    tasks = json.loads(render_goal_contract_file(goal))["tasks"]
    descriptions = [task["description"] for task in tasks]
    assert not any(text.startswith("Spawn independent native sub-agent") for text in descriptions)
    assert not any("livespec conventions refresh" in text for text in descriptions)
    assert any("read-only" in text and "gap report" in text for text in descriptions)
    assert not any(task["evidence_kind"] == "execution" for task in tasks)


@pytest.mark.parametrize("visual", [False, True])
@pytest.mark.parametrize(
    "flags,persists,executes,generates",
    [
        ("", True, True, True),
        ("--no-generate", True, True, False),
        ("--audit-only", True, False, False),
        ("--dry-run", False, False, False),
        ("--regenerate-missing", False, False, False),
        ("--regenerate-missing --confirm", False, False, True),
        ("--regenerate-missing --confirm --dry-run", False, False, False),
        ("--all --dry-run", False, False, False),
        ("--visual", True, False, True),
    ],
)
def test_test_report_generation_and_full_suite_follow_the_effective_mode(
    tmp_path: Path, flags: str, visual: bool, persists: bool, executes: bool, generates: bool
) -> None:
    goal = _goal(tmp_path, "spec-test", flags, visual)
    tasks = json.loads(render_goal_contract_file(goal))["tasks"]
    descriptions = [task["description"] for task in tasks]
    assert bool([text for text in descriptions if text.startswith(REPORT_WRITES)]) is persists
    full = [task for task in tasks if task["description"].startswith("Full test suite executed")]
    assert bool(full) is executes
    assert (
        bool([text for text in descriptions if text.startswith("Missing tests generated")])
        is generates
    )
    if full:
        assert full[0]["evidence_kind"] == "execution"
        assert typed_evidence_missing(
            full[0],
            {"output": "All tests passed", "success_criteria_met": True},
            contract=goal.payload,
            project_root=tmp_path,
        ) == ["execution_receipt_path"]
    if not persists and not generates:
        assert not any("write to strategy.md" in text for text in descriptions)
        assert not any(task["evidence_kind"] == "execution" for task in tasks)
    if flags == "--visual" and visual:
        assert any(task["id"].startswith("visual.gate_validate") for task in tasks)


def test_normal_fix_keeps_report_refresh_and_code_execution(tmp_path: Path) -> None:
    tasks = _goal(tmp_path, "spec-fix", "", False).payload["tasks"]
    assert any(
        task["description"].startswith("Spawn independent native sub-agent") for task in tasks
    )
    assert any("livespec conventions refresh" in task["description"] for task in tasks)
    assert any(task["evidence_kind"] == "execution" for task in tasks)


def test_full_suite_cli_proof_rejects_prose_and_keeps_the_task_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    goal = _goal(tmp_path, "spec-test", "", False)
    task = next(t for t in goal.payload["tasks"] if t["description"] == "Full test suite executed")
    contract = tmp_path / "contract.json"
    state = tmp_path / "state.json"
    contract.write_text(render_goal_contract_file(goal))
    state.write_text(render_goal_state_file(goal))
    contract_before = contract.read_bytes()
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "goal",
            "prove",
            "--contract",
            str(contract),
            "--state",
            str(state),
            "--task",
            task["id"],
            "--evidence",
            '{"output":"All tests passed","success_criteria_met":true}',
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    assert "execution_receipt_path" in result.output
    assert json.loads(state.read_text())["tasks"][task["id"]]["status"] == "pending"
    assert contract.read_bytes() == contract_before


@pytest.mark.parametrize("flags,captures", [("--regenerate-missing --confirm", False), ("", True)])
def test_behavioral_generation_reserves_baseline_and_metadata_storage_for_visual_execution(
    tmp_path: Path, flags: str, captures: bool
) -> None:
    tasks = json.loads(render_goal_contract_file(_goal(tmp_path, "spec-test", flags, True)))[
        "tasks"
    ]
    generation = next(
        task
        for task in tasks
        if "behavioral trait having visual_state Gherkin" in task["description"]
    )
    assert "generate toHaveScreenshot() assertions" in generation["description"]
    assert "store baseline" not in generation["description"]
    assert "generate [screenshot].meta.yml" not in generation["description"]
    storage = [
        task
        for task in tasks
        if "baselines/states/" in task["description"]
        and "[screenshot].meta.yml" in task["description"]
    ]
    assert bool(storage) is captures
    if captures:
        assert storage[0]["ordinal"] > generation["ordinal"]
