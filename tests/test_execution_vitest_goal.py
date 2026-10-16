"""The real implementation task consumes Vitest observations through native archive guards."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from tests.execution_vitest_fixture import FEATURE, VitestProject
from tests.execution_vitest_fixture import vitest_dependencies as vitest_dependencies
from tests.execution_vitest_fixture import vitest_project as vitest_project
from validator.execution_evidence import verify_execution_observation, verify_execution_receipt
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)
from validator.run_artifacts import recheck_receipts
from validator.run_receipts import verify_evidence_receipts

ROOT = Path(__file__).resolve().parents[1]
# Two real captures plus canonical compilation and archive guards form one acceptance scenario.
pytestmark = pytest.mark.acceptance


@dataclass
class GoalPair:
    """Own untouched compiler output and isolated native proof state."""

    # Goal APIs expose dynamic JSON; preserve their existing boundary rather than fabricate tasks.
    contract: dict[str, Any]
    state: dict[str, Any]
    contract_path: Path
    state_path: Path
    skill_path: Path

    def step_task(self) -> dict[str, Any]:
        """Select the actual canonical implementation step, retaining all other obligations."""
        tasks = [
            task
            for task in self.contract["tasks"]
            if task["description"]
            == "Execute each plan step with code, targeted tests, and step gate verification"
        ]
        assert len(tasks) == 1
        assert tasks[0]["evidence_kind"] == "execution"
        return tasks[0]


def _prepare_goal(project: Path, variant: str, *, historical: bool) -> GoalPair:
    directory = project.parent / f"goal-{variant}"
    directory.mkdir()
    producer = directory / "producer"
    canonical = ROOT / ".agent-sync/skills/spec-implement"
    skill = producer / ".agent-sync/skills/spec-implement"
    shutil.copytree(canonical, skill)
    skill_path = skill / "SKILL.md"
    if historical:
        skill_path.write_text(
            skill_path.read_text().replace(
                "Execute each plan step with code, targeted tests, and step gate verification "
                "<!-- evidence:execution outcome:passed -->",
                "Execute each plan step with code, targeted tests, and step gate verification "
                "<!-- evidence:execution -->",
            )
        )
    else:
        assert skill_path.read_bytes() == (canonical / "SKILL.md").read_bytes()
    goal = compile_command_goal(
        "spec-implement",
        project_root=project,
        livespec_root=producer,
        feature=FEATURE,
        flags="--auto",
    )
    contract_path, state_path = directory / "contract.json", directory / "state.json"
    contract_path.write_text(render_goal_contract_file(goal))
    state_path.write_text(render_goal_state_file(goal))
    return GoalPair(
        json.loads(contract_path.read_text()),
        json.loads(state_path.read_text()),
        contract_path,
        state_path,
        skill_path,
    )


def _prove(pair: GoalPair, project: Path, receipt: Path) -> dict[str, Any]:
    return prove_goal_task(
        pair.contract,
        pair.state,
        pair.step_task()["id"],
        {"execution_receipt_path": str(receipt)},
        project_root=project,
    )


def _historical_rejection(pair: GoalPair, project: Path, receipt: Path) -> dict[Path, bytes]:
    rejected = _prove(pair, project, receipt)
    assert not rejected["accepted"], rejected
    pair.state = rejected["state"]
    pair.state_path.write_text(json.dumps(pair.state))
    rejection = pair.state_path.with_name("rejected-proof.json")
    rejection.write_text(json.dumps(rejected))
    return {
        path: path.read_bytes()
        for path in (pair.contract_path, pair.state_path, pair.skill_path, rejection)
    }


def _archive_guard(pair: GoalPair, proof: dict[str, Any], project: Path) -> dict[str, Any]:
    task = pair.step_task()
    actual_state = proof["state"]["tasks"][task["id"]]
    checks = verify_evidence_receipts(
        [{**task, **actual_state}], project_root=project, feature=FEATURE, evidence_policy="2"
    )
    assert len(checks) == 1 and checks[0].verified
    assert checks[0].expected_outcome == "passed"
    entry = checks[0].to_dict()
    rechecked = recheck_receipts([entry], project_root=project, feature=FEATURE)
    assert len(rechecked) == 1 and rechecked[0].verified
    assert rechecked[0].expected_outcome == "passed"
    return entry


@pytest.mark.parametrize(
    "changed_input", ["vitest.config.ts", "package-lock.json"], ids=["config", "lock"]
)
def test_real_canonical_task016_proof_and_archive_guard_preserve_history_and_reject_drift(
    vitest_project: VitestProject,
    changed_input: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove the real generic step and its receipt guard without completing the full workflow."""
    project = vitest_project.root
    # Reproduce CI's absent personal hooks without injecting tasks or assuming an ordinal.
    monkeypatch.setattr(
        "validator.hook_resolver.GLOBAL_HOOKS_DIR", project.parent / "absent-global-hooks"
    )
    vitest_project.write("test('observed', () => { expect(1).toBe(1); });")
    old = _prepare_goal(project, "historical", historical=True)
    new = _prepare_goal(project, "canonical", historical=False)
    assert not old.step_task().get("evidence_expected_outcome")
    assert new.step_task()["evidence_expected_outcome"] == "passed"
    assert old.contract["goal_hash"] != new.contract["goal_hash"]
    old_receipt = vitest_project.capture()
    history = _historical_rejection(old, project, old_receipt)
    receipt = vitest_project.capture()
    assert receipt != old_receipt
    observed = verify_execution_observation(receipt, project, FEATURE, "passed")
    assert observed.valid and observed.certified_acs == [], observed.gaps
    assert not verify_execution_receipt(receipt, project, FEATURE).valid
    proof = _prove(new, project, receipt)
    # @spec AC-005: The actual compiled step accepts only its genuine passed observation.
    # — .specs/features/096-node-vitest-execution/spec.md#ac-005
    assert proof["accepted"], proof
    task_id = new.step_task()["id"]
    assert proof["state"]["tasks"][task_id]["status"] == "complete"
    assert all(
        task["status"] == "pending"
        for identifier, task in proof["state"]["tasks"].items()
        if identifier != task_id
    )
    # @spec AC-005: The native archive receipt guard rechecks the canonical passed purpose.
    # — .specs/features/096-node-vitest-execution/spec.md#ac-005
    entry = _archive_guard(new, proof, project)
    assert entry["expected_outcome"] == "passed" and entry["verified"]
    target = project / changed_input
    target.write_text(target.read_text() + "\n")
    drifted = _prove(new, project, receipt)
    # @spec AC-003: Bound input drift rejects both actual task proof and the archive recheck.
    # — .specs/features/096-node-vitest-execution/spec.md#ac-003
    assert not drifted["accepted"], drifted
    stale_guard = recheck_receipts([entry], project_root=project, feature=FEATURE)
    assert len(stale_guard) == 1 and not stale_guard[0].verified
    assert stale_guard[0].expected_outcome == "passed"
    assert all(path.read_bytes() == previous for path, previous in history.items())
    assert not _prove(old, project, receipt)["accepted"]
