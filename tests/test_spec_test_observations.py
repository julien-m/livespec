"""Canonical Test observations preserve independent final acceptance (078 FR-009)."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from tests.execution_vitest_fixture import FEATURE, VitestProject
from tests.execution_vitest_fixture import vitest_dependencies as vitest_dependencies
from tests.execution_vitest_fixture import vitest_project as vitest_project
from validator.evidence_applicability import resolve_applicability
from validator.execution_capture import capture_execution
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
    plan.write_text(PLAN.replace("npm test", "pytest tests/ --ignore=tests/integration/e2e"))
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


def _prepare_review_only_observation(
    vitest_project: VitestProject, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    """Prepare six review ACs and capture their independent genuine runtime observation."""
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
    package = project / "package.json"
    data = json.loads(package.read_text())
    data["scripts"] = {"test": "vitest run"}
    package.write_text(json.dumps(data))
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", project / "absent-hooks")
    vitest_project.write("test('observed', () => { expect(1).toBe(1); });")
    receipt = vitest_project.capture()
    observed = verify_execution_observation(receipt, project, FEATURE, "passed")
    assert observed.valid and observed.certified_acs == [], observed.gaps
    return project, receipt


def _prepare_historical_skill(project: Path) -> Path:
    """Preserve the old immutable generic-task purpose in a separate producer copy."""
    producer = project.parent / "historical-producer"
    shutil.copytree(
        ROOT / ".agent-sync/skills/spec-test", producer / ".agent-sync/skills/spec-test"
    )
    shutil.copytree(ROOT / "system", producer / "system")
    old_skill = producer / ".agent-sync/skills/spec-test/SKILL.md"
    old_skill.write_text(
        re.sub(r" suite:[a-z0-9-]+", "", old_skill.read_text()).replace(" outcome:passed", "")
    )
    return old_skill


@pytest.mark.acceptance
def test_canonical_test_goal_proves_real_observation_without_certifying_review_acs(
    vitest_project: VitestProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Current and historical canonical tasks retain their distinct proof purposes."""
    project, receipt = _prepare_review_only_observation(vitest_project, monkeypatch)
    old_skill = _prepare_historical_skill(project)
    producer = old_skill.parents[3]
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


def _suite_archive_errors(
    contract: dict[str, Any],
    generic: list[dict[str, Any]],
    receipt: Path,
    root: Path,
    extra: list[Path] | None = None,
) -> list[str]:
    """Recheck canonical suite scope at the existing policy2 archive boundary."""
    # The same immutable declaration is rechecked at both archive and archive-read boundaries.
    from validator.acceptance_evidence import archived_policy2_evidence_errors

    artifact = {
        "evidence_policy_version": "2",
        "evidence_contract": contract,
        "goal_hash": contract["goal_hash"],
        "feature": FEATURE,
        "flags": contract["normalized_flags"],
        "command": "spec-test",
        "goal": {
            "tasks": [
                {
                    "id": t["id"],
                    "status": "complete",
                    "accepted_evidence": {
                        "execution_receipt_path": str(receipt),
                        "execution_receipt_paths": [str(p) for p in extra or []],
                    },
                }
                for t in generic
            ]
        },
    }
    return archived_policy2_evidence_errors(artifact, root)


def _prepare_suite_commands(vitest_project: VitestProject) -> tuple[str, ...]:
    """Prepare two real package cwd units and distinct root integration/E2E selections."""
    root = vitest_project.root
    names = ("dashboard", "slides", "integration", "e2e")
    for index, name in enumerate(names):
        cwd = root / name if index < 2 else root
        if index < 2:
            cwd.mkdir()
            for file in ("package.json", "package-lock.json", "vitest.config.ts"):
                shutil.copy2(root / file, cwd / file)
            shutil.copytree(root / "node_modules", cwd / "node_modules")
        VitestProject(cwd, vitest_project.node).write(
            "test('observed', () => { expect(1).toBe(1); });", name + ".test.ts"
        )
        package = cwd / "package.json"
        data = json.loads(package.read_text())
        data.setdefault("scripts", {})[name] = "vitest run " + name + ".test.ts"
        package.write_text(json.dumps(data))
    plan = root / ".specs/features" / FEATURE / "plan.md"
    plan.write_text(
        "## Resolved Test Commands\n\n| Action | Command |\n|---|---|\n"
        + "".join(
            f"| {name} {'unit' if index < 2 else ''} | npm run {name}"
            + (f" ({name})" if index < 2 else "")
            + " |\n"
            for index, name in enumerate(names)
        )
    )
    return names


def _capture_suite(project: VitestProject, name: str) -> Path:
    """Capture declared cwd while keeping governing evidence at the project root."""
    cwd = project.root / name if name in {"dashboard", "slides"} else project.root
    result = capture_execution(
        [str(project.node), str(cwd / "node_modules/vitest/vitest.mjs"), "run", name + ".test.ts"],
        project_root=project.root,
        feature=FEATURE,
        adapter="junit",
        env=dict(os.environ),
        timeout=10,
        execution_cwd=cwd,
    )
    assert result.exit_code == 0, result.stderr
    return Path(result.receipt_path)


@pytest.mark.acceptance
def test_suite_observations_reject_wrong_selection_and_require_complete_aggregate(
    vitest_project: VitestProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Distinct genuine executions bind multiple unit aliases and every required suite."""
    root = vitest_project.root
    names = _prepare_suite_commands(vitest_project)
    plan = root / ".specs/features" / FEATURE / "plan.md"
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", root / "absent-hooks")
    goal = compile_command_goal(
        "spec-test",
        project_root=root,
        livespec_root=ROOT,
        feature=FEATURE,
        flags="--auto --no-generate --model=reviewer/v1",
    )
    contract = json.loads(render_goal_contract_file(goal))
    state = json.loads(render_goal_state_file(goal))
    receipts = [_capture_suite(vitest_project, name) for name in names]
    wrong_cwd = vitest_project.capture("--root", "dashboard", "dashboard.test.ts")
    generic = [
        t
        for t in contract["tasks"]
        if t["evidence_kind"] == "execution" and t.get("acceptance_scope") != "feature"
    ]
    assert len(generic) == 4
    evidence: dict[str, Any] = {"execution_receipt_path": str(receipts[0])}
    assert all(
        not prove_goal_task(contract, state, t["id"], evidence, project_root=root)["accepted"]
        for t in generic
    )
    wrong = {
        "execution_receipt_path": str(wrong_cwd),
        "execution_receipt_paths": [str(p) for p in receipts[1:]],
    }
    assert not prove_goal_task(contract, state, generic[0]["id"], wrong, project_root=root)[
        "accepted"
    ]
    assert any(
        "suite" in error
        for error in _suite_archive_errors(contract, generic, wrong_cwd, root, receipts[1:])
    )
    for task in generic:
        evidence["execution_receipt_paths"] = [str(p) for p in receipts[1:]]
        result = prove_goal_task(contract, state, task["id"], evidence, project_root=root)
        assert result["accepted"], result
    assert not _suite_archive_errors(contract, generic, receipts[0], root, receipts[1:])
    assert any(
        "suite" in error for error in _suite_archive_errors(contract, generic, receipts[0], root)
    )
    plan.write_text(plan.read_text() + "\nChanged declaration.\n")
    assert not prove_goal_task(contract, state, generic[0]["id"], evidence, project_root=root)[
        "accepted"
    ]
