"""Outcome-based goals: scope, stop condition, recovery and bounded retries (feature 081).

# @spec AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, AC-007, AC-008, AC-009
#   — .specs/features/081-lightweight-outcome-goals/spec.md
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator import init_from_code
from validator.cli import app
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)
from validator.goal_outcome import goal_requirement, stop_condition
from validator.init_profile import ObservedProfile

ROOT = Path(__file__).resolve().parents[1]
# validator/goal_*.py + init_goal_conventions.py on main 457a252, before feature 081.
GOAL_LINES_BEFORE_081 = 5813
SKILLS = ROOT / ".agent-sync" / "skills"
GOAL_SKILLS = {
    "spec-ship",
    "spec-feature",
    "spec-init",
    "spec-implement",
    "spec-specify",
    "spec-plan",
    "spec-test",
    "spec-fix",
}
RECEIPT_FAMILIES = (
    "hooks.before",
    "qe.analysis",
    "visual.",
    "finalize.registry",
    "conventions.gate",
    "outcome.verified",
    "archive.run",
)
QE = {
    "qe_dimensions_considered": ["functional_correctness"],
    "qe_gates_required": ["AC coverage matrix"],
    "qe_expected_evidence": ["test transcript"],
    "qe_gaps_or_missing_evidence": ["none"],
    "qe_boundary_note": "Review and audit stay separate from test evidence.",
}


REQUIREMENT_CASES = {
    ("spec-ship", ()): "required",
    ("spec-feature", ("--auto",)): "required",
    ("spec-feature", ("-a",)): "required",
    ("spec-feature", ()): "optional",
    ("spec-init", ("--auto", "--from-code")): "required",
    ("spec-init", ("--from-code",)): "optional",
    ("spec-implement", ()): "required",
    ("spec-implement", ("--step",)): "optional",
    ("spec-implement", ("--dry-run",)): "optional",
    ("spec-specify", ("--auto",)): "required",
    ("spec-specify", ()): "optional",
    ("spec-test", ("-a",)): "optional",  # -a is --audit-only for spec-test
    ("spec-check", ("--fix", "--all")): "optional",
    ("spec-status", ()): "optional",
    ("spec-explain", ()): "optional",
    ("spec-propose", ("--auto",)): "optional",
    ("spec-refine", ("--auto",)): "optional",
    ("spec-preflight", ("--fix", "--auto")): "optional",
    ("spec-init", ("-a",)): "required",
    ("spec-init", ("--auto", "--dry-run")): "optional",  # preview writes nothing
    ("spec-fix", ("--auto",)): "required",
}


def test_goal_requirement_targets_only_autonomous_long_runs() -> None:
    observed = {case: goal_requirement(case[0], case[1]) for case in REQUIREMENT_CASES}
    assert observed == REQUIREMENT_CASES


def test_stop_condition_scopes(tmp_path: Path) -> None:
    (tmp_path / ".specs/features/001-demo").mkdir(parents=True)
    assert stop_condition("spec-test", "001-demo", [], tmp_path)["argv"] == [
        "livespec",
        "validate",
        ".specs/features/001-demo",
    ]
    # A feature not created yet is never weakened to project scope.
    assert stop_condition("spec-specify", "002-new", [], tmp_path)["argv"][-1] == (
        ".specs/features/002-new"
    )
    assert stop_condition("spec-ship", None, [], tmp_path)["scope"] == "project"
    assert stop_condition("spec-init", None, ["--auto", "--from-code"], tmp_path)["argv"] == [
        "livespec",
        "init-from-code",
        "--verify-only",
    ]


def _contract_violations(command: str) -> list[str]:
    goal = compile_command_goal(
        command, project_root=ROOT, livespec_root=ROOT, flags="--auto --model=reviewer/v1"
    )
    tasks = goal.payload["tasks"]
    ids = [str(task["id"]) for task in tasks]
    problems = [f"{command}: {len(tasks)} tasks"] if len(tasks) > 10 else []
    if [task["ordinal"] for task in tasks] != list(range(1, len(tasks) + 1)):
        problems.append(f"{command}: ordinals")
    if ids[-2:] != ["outcome.verified", "archive.run"]:
        problems.append(f"{command}: tail {ids[-2:]}")
    problems.extend(
        f"{command}: {task['id']} is not receipt-backed"
        for task in tasks
        if not str(task["id"]).startswith(RECEIPT_FAMILIES)
        and task["evidence_kind"] not in ("execution", "review")
    )
    problems.extend(
        f"{command}: {task['id']} demands prose output"
        for task in tasks
        if "observable_output_or_artifact" in task["required_evidence"]
        and task["id"] != "outcome.verified"
    )
    stop = goal.payload["stop_condition"]
    if stop["argv"][0] != "livespec" or not stop["display"].startswith(" ".join(stop["argv"])):
        problems.append(f"{command}: stop condition")
    contract = json.loads(render_goal_contract_file(goal))
    if contract["schema_version"] != "3.0" or goal.payload["schema_version"] != "3.0":
        problems.append(f"{command}: schema")
    inventory = [*goal.payload["execution_tasks"], *goal.payload["definition_of_done"]]
    if contract["checklist"] != inventory:
        problems.append(f"{command}: checklist differs from the active inventory")
    return problems


def test_every_command_contract_keeps_only_receipt_backed_tasks() -> None:
    commands = sorted(path.parent.name for path in SKILLS.glob("spec-*/expectations.md"))
    contract_violations = [
        problem for command in commands for problem in _contract_violations(command)
    ]
    assert contract_violations == []


def _step0(text: str) -> str:
    match = re.search(r"^## STEP 0 — .*?(?=^## |^# )", text, re.M | re.S)
    return match.group(0) if match else ""


def _skill_violations(skill: Path) -> list[str]:
    name = skill.parent.name
    text = skill.read_text(encoding="utf-8")
    forbidden = ("ABSOLU", "/goal clear", "/goal slash command unavailable", "active goal exists")
    problems = [f"{name}: {token}" for token in forbidden if token in text]
    step0 = _step0(text)
    if name in GOAL_SKILLS:
        expected = ("## STEP 0 — Goal (autonomous runs)", "create_goal", "/goal", "warning")
        problems.extend(f"{name}: STEP 0 lacks {token}" for token in expected if token not in step0)
        if len(step0.splitlines()) > 20:
            problems.append(f"{name}: STEP 0 longer than 20 lines")
    elif "livespec goal render" in step0:
        problems.append(f"{name}: goal step in a short command")
    return problems


def test_skills_never_block_on_native_goal_and_lock_only_autonomous_runs() -> None:
    skill_violations = [
        problem
        for skill in sorted(SKILLS.glob("spec-*/SKILL.md"))
        for problem in _skill_violations(skill)
    ]
    assert skill_violations == []


def test_conventions_are_gated_once_per_feature_without_per_task_proofs(tmp_path: Path) -> None:
    from tests._goal_contracts_02 import _write_fail_conventions_receipt

    project = tmp_path / "project"
    (project / ".specs").mkdir(parents=True)
    receipt = _write_fail_conventions_receipt(project)  # also writes the gates file
    goal = compile_command_goal(
        "spec-implement", project_root=project, livespec_root=ROOT, feature="001-demo"
    )
    contract = json.loads(render_goal_contract_file(goal))
    names = {
        "required_conventions",
        "convention_domains_recorded",
        "convention_sources_read",
        "conventions_applied_to_output",
    }
    convention_problems = [name for name in names if name in contract["canonical_json"]]
    convention_problems += [] if "conventions" not in goal.payload else ["conventions payload"]
    gated = [
        str(task["id"])
        for task in contract["tasks"]
        if "conventions_receipt_path" in task["required_evidence"]
    ]
    convention_problems += [] if gated == ["conventions.gate"] else [f"gated tasks {gated}"]
    state = json.loads(render_goal_state_file(goal))
    rejected = prove_goal_task(
        contract,
        state,
        "conventions.gate",
        {"conventions_receipt_path": receipt.relative_to(project).as_posix()},
        project_root=project,
    )
    if "conventions_receipt_verdict_pass" not in rejected["missing_evidence"]:
        convention_problems.append("non-PASS receipt accepted")
    assert convention_problems == []


def test_runtime_goal_prompt_is_short_and_neutral() -> None:
    anti_drift = (ROOT / "system/anti-drift-block.md").read_text(encoding="utf-8")
    section = anti_drift.split("### Runtime goal contract", 1)[1].split("### ", 1)[0]
    prompt_problems = [
        token
        for token in ("MUST", "ABSOLU", "/goal clear", "BLOCKED and stop")
        if token in anti_drift
    ]
    prompt_problems += (
        [] if len(section.splitlines()) <= 15 else ["goal section longer than 15 lines"]
    )
    prompt_problems += (
        [] if "already active, update it when the tool allows" in section else ["no reuse rule"]
    )
    long_steps = [
        skill.parent.name
        for skill in SKILLS.glob("spec-*/SKILL.md")
        if len(_step0(skill.read_text(encoding="utf-8")).splitlines()) > 20
    ]
    prompt_problems += [f"long STEP 0: {name}" for name in long_steps]
    docs = {
        "README.md": ("outcome goal", "stop condition"),
        "system/expectations.md": ("stop_condition", "goal_requirement", "outcome.verified"),
        "system/spec-system.md": ("### Runtime goals", "runtime-goal-contract"),
        ".specs/spec-system.md": ("### Runtime goals", "runtime-goal-contract"),
    }
    for doc, needles in docs.items():
        text = (ROOT / doc).read_text(encoding="utf-8")
        prompt_problems += [f"{doc} lacks {needle}" for needle in needles if needle not in text]
    obsolete = ("goal_conventions.py", "init_goal_conventions.py")
    prompt_problems += [name for name in obsolete if (ROOT / "validator" / name).exists()]
    goal_code = [
        path.read_text(encoding="utf-8") for path in (ROOT / "validator").glob("goal_*.py")
    ]
    prompt_problems += (
        [] if not any("child_goal" in text for text in goal_code) else ["child-goal code"]
    )
    lines = sum(len(text.splitlines()) for text in goal_code)
    prompt_problems += [] if lines < GOAL_LINES_BEFORE_081 else [f"goal code grew to {lines} lines"]
    assert prompt_problems == []


def _spec_test_goal(project: Path) -> tuple[dict[str, object], dict[str, object]]:
    goal = compile_command_goal(
        "spec-test", project_root=project, livespec_root=ROOT, feature="001-demo"
    )
    return json.loads(render_goal_contract_file(goal)), json.loads(render_goal_state_file(goal))


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    feature = project / ".specs/features/001-demo"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# Demo\n## Acceptance Criteria\n### AC-001\nWorks.\n")
    return project


def test_three_rejections_hand_back_a_blocked_report_and_later_proof_still_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _project(tmp_path)
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "none")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "none")
    contract, state = _spec_test_goal(project)
    statuses = []
    for _ in range(3):
        result = prove_goal_task(
            contract, state, "qe.analysis", {"output": "x"}, project_root=project
        )
        statuses.append(result["status"])
        state = result["state"]
    assert statuses == ["REJECTED_NEEDS_ACTION", "REJECTED_NEEDS_ACTION", "BLOCKED"]
    handback = result["handback"]
    assert handback["attempts"] == 3 and len(handback["tried"]) == 3
    assert "qe_boundary_note" in handback["missing_evidence"]
    assert handback["report"].startswith("BLOCKED at step 1 - verification_failed - qe.analysis")
    from validator.goal_render import render_goal_status

    assert "blocked:1 (qe.analysis)" in render_goal_status(state)
    accepted = prove_goal_task(contract, state, "qe.analysis", QE, project_root=project)
    assert accepted["status"] == "ACCEPTED"
    assert "blocked" not in accepted["state"]["tasks"]["qe.analysis"]


def _render_saved(runner: CliRunner, controls: Path) -> tuple[Path, Path]:
    result = runner.invoke(
        app,
        ["goal", "render", "spec-test", "--feature", "demo", "--flags", "--auto", "--save"],
    )
    assert result.exit_code == 0, result.output
    match = re.search(r"contract-file:(\S+) \| state-file:(\S+)", result.output)
    assert match is not None
    return Path(match.group(1)), Path(match.group(2))


def test_drifted_contract_recompiles_in_place_and_keeps_valid_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _project(tmp_path)
    (project / ".specs/livespec-version").write_text((ROOT / "VERSION").read_text())
    controls = tmp_path / "controls"
    controls.mkdir()
    import tempfile

    monkeypatch.setattr(tempfile, "tempdir", str(controls))
    monkeypatch.setattr("validator.integrations.INTEGRATIONS_DIR", tmp_path / "none")
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", tmp_path / "none")
    monkeypatch.chdir(project)
    runner = CliRunner()
    contract_path, state_path = _render_saved(runner, controls)
    first = json.loads(contract_path.read_text())
    assert first["feature"] == "001-demo"  # unnumbered slug resolved for every command
    common = ["--contract", str(contract_path), "--state", str(state_path)]
    proved = runner.invoke(
        app, ["goal", "prove", *common, "--task", "qe.analysis", "--evidence", json.dumps(QE)]
    )
    assert proved.exit_code == 0, proved.output

    # Same goal re-rendered: progress is kept, not reset.
    _render_saved(runner, controls)
    assert json.loads(state_path.read_text())["tasks"]["qe.analysis"]["status"] == "complete"

    # Input drift: a project hook now adds before-test context.
    hooks = project / ".specs/hooks"
    hooks.mkdir()
    (hooks / "before-test.md").write_text("Run the smoke suite first.\n")
    result = runner.invoke(
        app, ["goal", "prove", *common, "--task", "outcome.verified", "--evidence", "{}"]
    )
    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    rewritten = json.loads(contract_path.read_text())
    state = json.loads(state_path.read_text())
    # Re-rendering the drifted goal adopts the progress of the pair recompiled in place.
    new_contract_path, new_state_path = _render_saved(runner, controls)
    adopted = json.loads(new_state_path.read_text())
    recompile_facts = {
        "from_hash": output["recompiled"]["from_hash"] == first["goal_hash"],
        "carried": output["recompiled"]["carried"],
        "rewritten_in_place": rewritten["goal_hash"] == output["recompiled"]["to_hash"],
        "state_hash": state["goal_hash"] == rewritten["goal_hash"],
        "hook_task_added": rewritten["tasks"][0]["id"],
        "qe_status": state["tasks"]["qe.analysis"]["status"],
        "outcome_status": state["tasks"]["outcome.verified"]["status"],
        "recompiled_from": state["recompiled_from"] == first["goal_hash"],
        "rerender_new_paths": new_contract_path != contract_path,
        "rerender_adopts_qe": adopted["tasks"]["qe.analysis"]["status"],
    }
    assert recompile_facts == {
        "from_hash": True,
        "carried": ["qe.analysis"],
        "rewritten_in_place": True,
        "state_hash": True,
        "hook_task_added": "hooks.before",
        "qe_status": "complete",
        "outcome_status": "complete",
        "recompiled_from": True,
        "rerender_new_paths": True,
        "rerender_adopts_qe": "complete",
    }


@pytest.mark.real_stop_condition
def test_outcome_runs_the_real_stop_condition_and_rejects_invalid_specs(tmp_path: Path) -> None:
    project = _project(tmp_path)
    contract, state = _spec_test_goal(project)
    result = prove_goal_task(
        contract,
        state,
        "outcome.verified",
        {"exit_code": 0, "output": "all good"},
        project_root=project,
    )
    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert result["missing_evidence"] == ["stop_condition_exit_zero"]
    assert result["observed"]["exit_code"] != 0
    assert "spec.md" in result["observed"]["output_tail"]


def test_completed_autonomous_init_is_not_failed_by_an_elapsed_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = object.__new__(ObservedProfile)
    for name in ("_install", "_ensure_core", "_install_hooks", "verify_current_profile"):
        monkeypatch.setattr(init_from_code, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(init_from_code, "run_probes", lambda *args: ())
    monkeypatch.setattr(init_from_code, "render_preflight", lambda results: "READY")
    monkeypatch.setattr(init_from_code, "detect_profile", lambda root: profile)
    monkeypatch.setattr(init_from_code, "_integration_artifacts", lambda root: {})
    monkeypatch.setattr(init_from_code, "render_manifest", lambda profile, documents: "{}")
    writes: list[str] = []
    monkeypatch.setattr(
        init_from_code, "write_atomic", lambda root, path, text: writes.append(path.name)
    )
    expired = time.monotonic() - 1
    init_from_code._generate(tmp_path, init_from_code.InitOptions(tmp_path), profile, {}, expired)
    assert writes[-1] == "bootstrap-recap.md"


@pytest.mark.real_stop_condition
def test_stop_condition_launch_failure_is_rejected_with_the_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _project(tmp_path)
    contract, state = _spec_test_goal(project)

    def unavailable(*args: object, **kwargs: object) -> None:
        raise OSError("interpreter unavailable")

    monkeypatch.setattr("validator.goal_outcome.subprocess.run", unavailable)
    result = prove_goal_task(contract, state, "outcome.verified", {}, project_root=project)
    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert result["observed"]["exit_code"] == 127
    assert "interpreter unavailable" in result["observed"]["output_tail"]


def test_failed_recompile_blocks_without_certifying_stale_obligations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from validator.exceptions import ExpectationsInvalid
    from validator.goal_recompile import GoalRecompileError, refresh_goal

    project = _project(tmp_path)
    contract, state = _spec_test_goal(project)
    contract["goal_hash"] = "0" * 64  # pretend the inputs drifted

    def broken(*args: object, **kwargs: object) -> None:
        raise ExpectationsInvalid("expectations.md", "removed")

    monkeypatch.setattr("validator.goal_recompile.compile_goal", broken)
    before = (json.dumps(contract, sort_keys=True), json.dumps(state, sort_keys=True))
    with pytest.raises(GoalRecompileError, match="recompile failed"):
        refresh_goal(contract, state, project_root=project, livespec_root=ROOT)
    assert (json.dumps(contract, sort_keys=True), json.dumps(state, sort_keys=True)) == before


@pytest.mark.real_stop_condition
def test_outcome_rules_cover_exit_launch_timeout_and_silent_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    project = _project(tmp_path)
    (project / "report.txt").write_text("checked\n", encoding="utf-8")
    contract, state = _spec_test_goal(project)

    def runner(code: int | None, output: str, error: Exception | None = None):
        def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            if error is not None:
                raise error
            return subprocess.CompletedProcess(args, code or 0, stdout=output, stderr="")

        return run

    cases = {
        "nonzero_exit": (runner(1, "ERROR spec.md"), {"exit_code": 0, "output": "fine"}),
        "launch_failure": (runner(None, "", OSError("no interpreter")), {}),
        "timeout": (runner(None, "", subprocess.TimeoutExpired("livespec", 300)), {}),
        "exit0_with_output": (runner(0, "OK spec.md"), {}),
        "exit0_silent_artifact": (runner(0, ""), {"artifact": "report.txt"}),
        "exit0_silent_declared_text": (runner(0, ""), {"output": "trust me", "exit_code": 0}),
    }
    observed = {}
    for name, (run, evidence) in cases.items():
        monkeypatch.setattr("validator.goal_outcome.subprocess.run", run)
        result = prove_goal_task(
            contract, state, "outcome.verified", evidence, project_root=project
        )
        observed[name] = result["status"]
    assert observed == {
        "nonzero_exit": "REJECTED_NEEDS_ACTION",
        "launch_failure": "REJECTED_NEEDS_ACTION",
        "timeout": "REJECTED_NEEDS_ACTION",
        "exit0_with_output": "ACCEPTED",
        "exit0_silent_artifact": "ACCEPTED",
        "exit0_silent_declared_text": "REJECTED_NEEDS_ACTION",
    }
