"""Regression proof for autonomous, interactive and preview init goals."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.goal_contracts import GoalContract, compile_command_goal
from validator.verify_output import evaluate_rules

ROOT = Path(__file__).resolve().parents[1]
INTERVIEW_TASKS = (
    "If no brainstorm: run 6-question conversational interview (Q1-Q6)",
    "Present project profile summary and confirm before proceeding",
    "Accept stack adjustments and confirm final stack",
    "Ask dev tooling preferences (package manager, linter)",
)


def _render(project: Path, flags: str) -> GoalContract:
    return compile_command_goal("spec-init", project_root=project, livespec_root=ROOT, flags=flags)


# @spec AC-006: Distinct init obligations
#   — .specs/features/080-autonomous-from-code-recovery/spec.md#ac-006
@pytest.mark.parametrize("flags", ["--from-code --auto", "-f -a", "--auto -f"])
def test_autonomous_inventory_omits_interviews_and_retains_closure(
    tmp_path: Path, flags: str
) -> None:
    payload = _render(tmp_path / "project", flags).payload
    inventory = payload["execution_tasks"]
    assert not any(task in inventory for task in INTERVIEW_TASKS)
    for obligation in (
        "observed profile",
        "Create .specs/ directory",
        "sync-agent-assets.sh",
        "verify-only",
        "after-init hook",
    ):
        assert any(obligation in task for task in inventory), obligation
    assert any(task["id"] == "archive.run" for task in payload["tasks"])


@pytest.mark.parametrize("flags", ["", "--from-code", "--auto", "-f"])
def test_interactive_inventory_retains_original_interview_obligations(
    tmp_path: Path, flags: str
) -> None:
    inventory = _render(tmp_path / "project", flags).payload["execution_tasks"]
    assert all(task in inventory for task in INTERVIEW_TASKS)


@pytest.mark.parametrize("flags", ["--from-code --auto --dry-run", "-f -a -d"])
def test_preview_inventory_does_not_require_project_mutation(tmp_path: Path, flags: str) -> None:
    project = tmp_path / "preview"
    project.mkdir()
    payload = _render(project, flags).payload
    inventory = payload["execution_tasks"]
    assert any("preview" in task.lower() for task in inventory)
    assert not any("Create .specs/ directory" in task for task in inventory)
    assert not any("Execute hooks in order" in task for task in inventory)
    assert list(project.iterdir()) == []


def test_render_preserves_selected_target_and_force_without_rewriting_history(
    tmp_path: Path,
) -> None:
    project = tmp_path / "selected project"
    project.mkdir()
    old_payload = _render(project, "--from-code").payload
    historical = tmp_path / "historical.contract.json"
    historical.write_text(json.dumps(old_payload, sort_keys=True), encoding="utf-8")
    before = historical.read_bytes()
    payload = _render(project, f'--from-code --auto --force --dir "{project}"').payload
    assert payload["project_root"] == str(project.resolve())
    assert "--force" in payload["normalized_flags"]
    assert f"--dir={project}" in payload["normalized_flags"]
    assert historical.read_bytes() == before
    assert list(project.iterdir()) == []


def test_autonomous_skill_normalizes_before_lock_and_requires_current_closure() -> None:
    body = (ROOT / ".agent-sync/skills/spec-init/SKILL.md").read_text(encoding="utf-8")
    lock = body.split("## STEP 0", 1)[1].split("# Command:", 1)[0]
    assert lock.index("--from-code --auto") < lock.index("livespec goal render spec-init")
    autonomous = body.split("### Non-Interactive Autonomous From-Code Mode", 1)[1]
    autonomous = autonomous.split("## From-Code Mode", 1)[0]
    assert '"$TARGET_DIR"' in autonomous
    assert "INIT_ARGS+=(--force)" in autonomous
    assert "INIT_ARGS+=(--dry-run)" in autonomous
    assert "--verify-only" in autonomous
    assert "goal archive" in autonomous
    assert "return immediately" not in autonomous
    assert "--deep" in autonomous and "--stack" in autonomous


@pytest.mark.parametrize("flags", ["--from-code --auto", "-f -a", "--from-code --auto --force"])
def test_public_render_selects_same_autonomous_profile_for_aliases_and_target(
    tmp_path: Path, flags: str
) -> None:
    project = tmp_path / "selected project"
    project.mkdir()
    result = CliRunner().invoke(
        app,
        ["goal", "render", "spec-init", "--flags", f'{flags} --dir "{project}"', "--json"],
    )
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.output)
    payload = envelope["canonical"]
    assert payload["project_root"] == str(project.resolve())
    assert not any(task in payload["execution_tasks"] for task in INTERVIEW_TASKS)
    assert any(task["id"] == "archive.run" for task in payload["tasks"])
    assert list(project.iterdir()) == []


@pytest.mark.parametrize("flags", ["--from-code --auto --dry-run", "-f -a -d"])
def test_preview_verify_contract_replaces_installation_success_rules(
    tmp_path: Path, flags: str
) -> None:
    payload = _render(tmp_path / "project", flags).payload
    branches = payload["verify_rules"]["when"]
    flag = "-d" if "-d" in flags.split() else "--dry-run"
    preview = next(branch for branch in branches if branch["flag"] == flag)
    assert preview["replace_base"] is True
    report = evaluate_rules(
        payload["verify_rules"],
        artifact={"exit_code": 0, "stdout": "Preview: no changes applied"},
        active_flags=payload["normalized_flags"],
        feature=None,
        project_root=tmp_path,
    )
    assert report.outcome == "success"
    assert all(rule.status == "PASS" for rule in report.rules)
    false_success = evaluate_rules(
        payload["verify_rules"],
        artifact={"exit_code": 0, "stdout": "Preview: no changes applied\nLiveSpec initialized"},
        active_flags=payload["normalized_flags"],
        feature=None,
        project_root=tmp_path,
    )
    assert false_success.outcome == "drift"
    assert not any("roadmap.md" in item for item in payload["definition_of_done"])


def test_public_save_new_profile_preserves_prior_contract_and_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    controls = tmp_path / "controls"
    controls.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(controls))
    runner = CliRunner()
    prior = runner.invoke(
        app, ["goal", "render", "spec-init", "--flags", f"--dir {project}", "--save"]
    )
    assert prior.exit_code == 0, prior.output
    saved_paths = sorted((controls / "livespec-goals").iterdir())
    prior_bytes = {path: path.read_bytes() for path in saved_paths}
    current = runner.invoke(
        app,
        [
            "goal",
            "render",
            "spec-init",
            "--flags",
            f"--from-code --auto --dir {project}",
            "--save",
        ],
    )
    assert current.exit_code == 0, current.output
    assert len(saved_paths) == 2
    assert len(list((controls / "livespec-goals").iterdir())) == 4
    assert all(path.read_bytes() == before for path, before in prior_bytes.items())
    assert list(project.iterdir()) == []


@pytest.mark.parametrize("flags", ["--from-code --auto --dry-run", "-f -a -d"])
def test_preview_existing_visual_feature_cannot_require_scaffolding(
    tmp_path: Path, flags: str
) -> None:
    feature = "001-preview-ui"
    feature_dir = tmp_path / ".specs/features" / feature
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# UI\n\n## Screens\n", encoding="utf-8")
    payload = compile_command_goal(
        "spec-init", project_root=tmp_path, livespec_root=ROOT, feature=feature, flags=flags
    ).payload
    assert payload["runtime_context"]["is_visual_feature"] is True
    assert not any("Scaffold visual" in task for task in payload["execution_tasks"])
    assert not any("Create .specs/" in task for task in payload["execution_tasks"])
