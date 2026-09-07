"""Preserved test cases and fixtures for test_goal_contracts.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests._goal_contracts_01 import _fixture_roots, _repo_root, _write_execution_task_skill
from tests._goal_contracts_02 import _write_complete_check_fix_scenario, _write_conventions
from tests._goal_contracts_08 import _finalize_contract_and_state, _finalize_fixture
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)


def test_goal_prove_accepts_valid_finalize_receipt(tmp_path: Path) -> None:
    """AC-007: a real PASS receipt from finalize verify completes the task."""
    from validator.finalize import ApplyRequest, apply_finalization, verify_finalization

    project_root, livespec_root = _finalize_fixture(tmp_path)
    request = ApplyRequest(
        feature_slug="004-notifications",
        command="spec-demo",
        status="Implemented",
        entry_body="Feature: Implemented notifications",
        global_summary="[Feature 004] Implemented: Notifications",
        run_id="goal-run",
    )
    apply_finalization(project_root, request)
    verify_result = verify_finalization(
        project_root,
        "004-notifications",
        expected_command="spec-demo",
        run_id="goal-run",
    )
    assert verify_result.verdict == "PASS"
    contract, state = _finalize_contract_and_state(project_root, livespec_root)
    result = prove_goal_task(
        contract,
        state,
        "finalize.registry",
        evidence={"finalize_receipt_path": str(verify_result.receipt_path)},
        project_root=project_root,
    )
    assert result["status"] == "ACCEPTED"
    assert result["state"]["tasks"]["finalize.registry"]["status"] == "complete"


def test_goal_prove_rejects_tampered_finalize_receipt(tmp_path: Path) -> None:
    """AC-008 / SC-004: a registry file edited after verify makes the receipt
    stale; the proof must be rejected with the named evidence."""
    from validator.finalize import ApplyRequest, apply_finalization, verify_finalization

    project_root, livespec_root = _finalize_fixture(tmp_path)
    request = ApplyRequest(
        feature_slug="004-notifications",
        command="spec-demo",
        status="Implemented",
        entry_body="Feature: Implemented notifications",
        global_summary="[Feature 004] Implemented: Notifications",
        run_id="goal-run",
    )
    apply_finalization(project_root, request)
    verify_result = verify_finalization(
        project_root,
        "004-notifications",
        expected_command="spec-demo",
        run_id="goal-run",
    )
    readme = project_root / ".specs" / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8")
    contract, state = _finalize_contract_and_state(project_root, livespec_root)
    result = prove_goal_task(
        contract,
        state,
        "finalize.registry",
        evidence={"finalize_receipt_path": str(verify_result.receipt_path)},
        project_root=project_root,
    )
    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert any(item.startswith("finalize_receipt_valid:") for item in result["missing_evidence"])


def test_goal_prove_rejects_fail_verdict_finalize_receipt(tmp_path: Path) -> None:
    """AC-008: a FAIL-verdict receipt names the PASS requirement."""
    from validator.finalize import ApplyRequest, apply_finalization, verify_finalization

    project_root, livespec_root = _finalize_fixture(tmp_path)
    request = ApplyRequest(
        feature_slug="004-notifications",
        command="spec-demo",
        status="Implemented",
        entry_body="Feature: Implemented notifications",
        global_summary="[Feature 004] Implemented: Notifications",
        run_id="goal-run",
    )
    apply_finalization(project_root, request)
    # Corrupt the registry BEFORE verify so verify emits a FAIL receipt whose
    # file hashes still match the (corrupted) on-disk state.
    readme = project_root / ".specs" / "README.md"
    readme.write_text(
        "\n".join(
            line
            for line in readme.read_text(encoding="utf-8").splitlines()
            if "004-notifications" not in line and not line.startswith("| 004 ")
        ),
        encoding="utf-8",
    )
    verify_result = verify_finalization(
        project_root,
        "004-notifications",
        expected_command="spec-demo",
        run_id="goal-run-fail",
    )
    assert verify_result.verdict == "FAIL"
    contract, state = _finalize_contract_and_state(project_root, livespec_root)
    result = prove_goal_task(
        contract,
        state,
        "finalize.registry",
        evidence={"finalize_receipt_path": str(verify_result.receipt_path)},
        project_root=project_root,
    )
    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "finalize_receipt_verdict_pass" in result["missing_evidence"]


@pytest.mark.parametrize(
    "command",
    ["spec-specify", "spec-plan", "spec-implement", "spec-fix", "spec-stack", "spec-feature"],
)
def test_six_registry_commands_carry_finalize_registry_task(
    tmp_path: Path,
    command: str,
) -> None:
    """FR-005 (AC-007): every registry-finalizing command's real contract must
    include the finalize.registry task so DONE structurally requires the receipt."""
    project_root = tmp_path / "project"
    (project_root / ".specs").mkdir(parents=True)
    _write_conventions(project_root, tmp_path / "ai")
    feature = _write_complete_check_fix_scenario(project_root)
    goal = compile_command_goal(
        command,
        project_root=project_root,
        livespec_root=_repo_root(),
        feature=feature,
        flags="",
    )
    contract = json.loads(render_goal_contract_file(goal))
    finalize_tasks = [task for task in contract["tasks"] if task["id"] == "finalize.registry"]
    assert finalize_tasks, f"{command} contract lacks the finalize.registry task"
    assert "finalize_receipt_path" in finalize_tasks[0]["required_evidence"]


# ─── archive.run injected task (Feature 059, FR-001/FR-002/FR-003) ───────────


def _demo_contract_and_state(
    project_root: Path,
    livespec_root: Path,
    *,
    feature: str | None = "001-demo",
    flags: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compile the spec-demo fixture goal and return contract+state dicts."""
    goal = compile_command_goal(
        "spec-demo",
        project_root=project_root,
        livespec_root=livespec_root,
        feature=feature,
        flags=flags,
    )
    return (
        json.loads(render_goal_contract_file(goal)),
        json.loads(render_goal_state_file(goal)),
    )


@pytest.mark.parametrize(
    ("with_execution_tasks", "feature", "flags"),
    [
        (False, None, ""),
        (False, "001-demo", "--strict"),
        (True, None, ""),
        (True, "001-demo", "--strict --auto"),
    ],
)
def test_every_contract_carries_exactly_one_archive_run_task(
    tmp_path: Path,
    with_execution_tasks: bool,
    feature: str | None,
    flags: str,
) -> None:
    """AC-001: archive.run is injected compiler-side for every command/feature/flags."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    if with_execution_tasks:
        _write_execution_task_skill(livespec_root)

    contract, state = _demo_contract_and_state(
        project_root, livespec_root, feature=feature, flags=flags
    )

    archive_tasks = [task for task in contract["tasks"] if task["id"] == "archive.run"]
    assert len(archive_tasks) == 1
    assert "archive.run" in state["tasks"]
    assert state["tasks"]["archive.run"]["status"] == "pending"


def test_archive_run_task_has_strictly_highest_ordinal(tmp_path: Path) -> None:
    """AC-002: archive.run snapshots all prior evidence — always the last ordinal."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_execution_task_skill(livespec_root)

    contract, _state = _demo_contract_and_state(project_root, livespec_root)

    archive_task = next(task for task in contract["tasks"] if task["id"] == "archive.run")
    other_ordinals = [task["ordinal"] for task in contract["tasks"] if task["id"] != "archive.run"]
    assert all(archive_task["ordinal"] > ordinal for ordinal in other_ordinals)
    assert archive_task["ordinal"] == max(task["ordinal"] for task in contract["tasks"])


def test_archive_run_task_evidence_family_matches_constants(tmp_path: Path) -> None:
    """AC-003: required evidence, named substitutes, and repair actions are fixed."""
    project_root, livespec_root = _fixture_roots(tmp_path)

    contract, _state = _demo_contract_and_state(project_root, livespec_root)

    task = next(task for task in contract["tasks"] if task["id"] == "archive.run")
    assert task["required_evidence"] == ["run_artifact_path"]
    assert task["invalid_substitutes"] == [
        "prose_archive_claim",
        "exit_code_without_artifact",
        "tmpdir_contract_state_paths_without_artifact",
    ]
    assert task["category"] == "injected"
    assert "livespec goal archive" in task["description"]
    assert any("livespec goal archive" in action for action in task["repair_if_missing"])
    assert any("artifact path" in action for action in task["repair_if_missing"])


def test_archive_run_task_skips_convention_evidence_layering(tmp_path: Path) -> None:
    """AC-003: the synthetic compiler task never carries convention proof fields."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    _write_conventions(project_root, tmp_path / "ai")
    _write_execution_task_skill(livespec_root)

    contract, _state = _demo_contract_and_state(project_root, livespec_root)

    task = next(task for task in contract["tasks"] if task["id"] == "archive.run")
    assert task["required_evidence"] == ["run_artifact_path"]
    assert "required_conventions" not in task
    # Prose tasks keep convention layering — the injection must not strip them.
    prose_task = contract["tasks"][0]
    assert "convention_domains_recorded" in prose_task["required_evidence"]


def test_archive_run_injection_preserves_hash_determinism(tmp_path: Path) -> None:
    """AC-002: same inputs → same canonical JSON and hash with the injected task."""
    project_root, livespec_root = _fixture_roots(tmp_path)

    rendered = [
        compile_command_goal(
            "spec-demo",
            project_root=project_root,
            livespec_root=livespec_root,
            feature="001-demo",
            flags="--strict",
        )
        for _ in range(5)
    ]

    first = rendered[0]
    assert all(goal.goal_hash == first.goal_hash for goal in rendered)
    assert all(goal.canonical_json == first.canonical_json for goal in rendered)
    assert '"archive.run"' in first.canonical_json


# ─── archive.run prove validator (Feature 059, FR-003) ───────────────────────


def _archive_fixture_artifact(
    project_root: Path,
    contract: dict[str, Any],
    state: dict[str, Any],
) -> Path:
    """Archive the fixture goal and return the written artifact path."""
    from validator.run_artifacts import archive_goal_run

    result = archive_goal_run(contract, state, project_root=project_root, exit_code=0)
    assert result.path is not None
    return result.path


def test_archive_run_prove_rejects_prose_claim(tmp_path: Path) -> None:
    """AC-003: prose without an artifact path names prose_archive_claim."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"output": "I archived the run", "success_criteria_met": True},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "prose_archive_claim" in result["invalid_substitutes"]
    assert "run_artifact_path" in result["missing_evidence"]
    assert any("livespec goal archive" in action for action in result["required_actions"])
    assert result["state"]["tasks"]["archive.run"]["status"] == "pending"


def test_archive_run_prove_rejects_exit_code_substitute(tmp_path: Path) -> None:
    """AC-003: an exit code is not an artifact."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"exit_code": 0},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "exit_code_without_artifact" in result["invalid_substitutes"]


def test_archive_run_prove_rejects_tmpdir_contract_state_paths(tmp_path: Path) -> None:
    """AC-003: $TMPDIR contract/state paths are not the durable artifact."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={
            "contract_file": "/tmp/livespec-goals/goal-spec-demo-abcd1234.contract.json",
            "state_file": "/tmp/livespec-goals/goal-spec-demo-abcd1234.state.json",
        },
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "tmpdir_contract_state_paths_without_artifact" in result["invalid_substitutes"]


def test_archive_run_prove_rejects_path_outside_specs_runs(tmp_path: Path) -> None:
    """AC-004: containment — the artifact must live under .specs/.runs/."""
    project_root, livespec_root = _fixture_roots(tmp_path)
    contract, state = _demo_contract_and_state(project_root, livespec_root)
    outside = project_root / "artifact.json"
    outside.write_text("{}", encoding="utf-8")

    result = prove_goal_task(
        contract,
        state,
        "archive.run",
        evidence={"run_artifact_path": str(outside)},
        project_root=project_root,
    )

    assert result["status"] == "REJECTED_NEEDS_ACTION"
    assert "run_artifact_under_specs_runs" in result["missing_evidence"]
