"""Canonical Test observations preserve independent final acceptance (078 FR-009)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests.execution_vitest_fixture import FEATURE, VitestProject
from tests.execution_vitest_fixture import vitest_dependencies as vitest_dependencies
from tests.execution_vitest_fixture import vitest_project as vitest_project
from validator.evidence_applicability import resolve_applicability
from validator.execution_evidence import verify_execution_observation
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)
from validator.run_artifacts import recheck_receipts
from validator.run_receipts import verify_evidence_receipts

ROOT = Path(__file__).resolve().parents[1]
PLAN = """## Resolved Test Commands

| Action | Command (working directory) | Tool | Status |
|---|---|---|---|
| Unit | npm test | Vitest | Resolved |
| Integration / E2E / visual / Python / full suite | Not run | Excluded | Not applicable |
"""


def test_explicit_absence_and_resolved_commands_have_distinct_applicability(tmp_path: Path) -> None:
    """A suite label in an explicit N/A row is not an executable declaration."""
    directory = tmp_path / ".specs/features" / FEATURE
    directory.mkdir(parents=True)
    (directory / "spec.md").write_text("# Nonvisual command contract\n")
    plan = directory / "plan.md"
    plan.write_text(PLAN)
    absent = [
        resolve_applicability(tmp_path, FEATURE, p)["applicable"]
        for p in ("integration-command", "e2e-command")
    ]
    plan.write_text(
        PLAN + "| Integration | `npm run test:integration` | Vitest | Resolved |\n"
        "| E2E | `npx playwright test` | Playwright | Resolved |\n"
    )
    declared = [
        resolve_applicability(tmp_path, FEATURE, p)["applicable"]
        for p in ("integration-command", "e2e-command")
    ]
    assert (absent, declared) == ([False, False], [True, True])


@pytest.mark.acceptance
def test_canonical_test_goal_proves_real_observation_without_certifying_review_acs(
    vitest_project: VitestProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Current and historical canonical tasks retain their distinct proof purposes."""
    project = vitest_project.root
    directory = project / ".specs/features" / FEATURE
    (directory / "spec.md").write_text(
        "# Nonvisual workflow contract\n"
        + "".join(
            f"\n## AC-{number:03d}\nReview workflow configuration.\n"
            "**Evidence:** review\n**Review inputs:** [workflow](workflow.md)\n"
            for number in range(1, 7)
        )
    )
    (directory / "workflow.md").write_text("The workflow runs package tests.\n")
    (directory / "plan.md").write_text(PLAN.split("| Integration / E2E")[0])
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", project / "absent-hooks")
    vitest_project.write("test('observed', () => { expect(1).toBe(1); });")
    receipt = vitest_project.capture()
    observed = verify_execution_observation(receipt, project, FEATURE, "passed")
    assert observed.valid and observed.certified_acs == [], observed.gaps
    producer = project.parent / "historical-producer"
    shutil.copytree(
        ROOT / ".agent-sync/skills/spec-test", producer / ".agent-sync/skills/spec-test"
    )
    shutil.copytree(ROOT / "system", producer / "system")
    old_skill = producer / ".agent-sync/skills/spec-test/SKILL.md"
    old_skill.write_text(old_skill.read_text().replace(" outcome:passed", ""))
    history = old_skill.read_bytes()
    for livespec_root, historical in ((producer, True), (ROOT, False)):
        goal = compile_command_goal(
            "spec-test",
            project_root=project,
            livespec_root=livespec_root,
            feature=FEATURE,
            flags="--auto --update --model=reviewer/v1",
        )
        contract = json.loads(render_goal_contract_file(goal))
        state = json.loads(render_goal_state_file(goal))
        generic = [
            t
            for t in contract["tasks"]
            if t["evidence_kind"] == "execution" and t.get("acceptance_scope") != "feature"
        ]
        assert len(generic) == 2  # Unit and DoD; integration/E2E are explicitly absent.
        for task in generic:
            proof = prove_goal_task(
                contract,
                state,
                task["id"],
                {"execution_receipt_path": str(receipt)},
                project_root=project,
            )
            assert proof["accepted"] is not historical, proof
            if not historical:
                checks = verify_evidence_receipts(
                    [{**task, **proof["state"]["tasks"][task["id"]]}],
                    project_root=project,
                    feature=FEATURE,
                    evidence_policy="2",
                )
                assert len(checks) == 1 and checks[0].verified
                assert recheck_receipts(
                    [checks[0].to_dict()], project_root=project, feature=FEATURE
                )[0].verified
        acceptance = [t for t in contract["tasks"] if t.get("acceptance_scope") == "feature"]
        assert len(acceptance) == 1
        assert len(acceptance[0]["expected_evidence"]["acceptance_inventory"]) == 6
        assert not acceptance[0].get("evidence_expected_outcome")
        rejected = prove_goal_task(
            contract,
            state,
            acceptance[0]["id"],
            {"execution_receipt_path": str(receipt)},
            project_root=project,
        )
        assert not rejected["accepted"]
    assert old_skill.read_bytes() == history
