"""Resolved action purposes freeze every command without certifying unsupported drivers."""

from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any

import pytest

from validator.acceptance_evidence import archived_policy2_evidence_errors
from validator.evidence_applicability import _command_key, resolve_applicability, suite_binding
from validator.execution_capture import capture_execution
from validator.execution_evidence import verify_execution_observation
from validator.goal_contracts import (
    compile_command_goal,
    prove_goal_task,
    render_goal_contract_file,
    render_goal_state_file,
)

FEATURE = "001-commands"
ROOT = Path(__file__).resolve().parents[1]


def _project(root: Path, rows: list[tuple[str, str]]) -> Path:
    """Write real commands and one review-only acceptance declaration before execution."""
    feature = root / ".specs/features" / FEATURE
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text(
        "# Nonvisual command contract\n\n## AC-001\nReview configuration.\n"
        "**Evidence:** review\n**Review inputs:** [workflow](workflow.md)\n"
    )
    (feature / "workflow.md").write_text("Review the declared commands.\n")
    (feature / "plan.md").write_text(
        "## Resolved Test Commands\n\nThese commands retain their declared purpose.\n\n"
        "| Action | Command |\n|---|---|\n"
        + "".join(f"| {action} | `{command}` |\n" for action, command in rows)
    )
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_one.py").write_text("def test_one():\n    assert 1 + 1 == 2\n")
    return feature


@pytest.mark.parametrize(
    "action",
    [
        "Focused behavior",
        "CLI/purpose regression",
        "Capture regression",
        "Cargo compatibility",
        "Focused guard tests",
        "Neighbor regressions",
        "Run tests",
        "Behavior tests",
    ],
)
def test_test_purpose_actions_freeze_original_unit_selection(tmp_path: Path, action: str) -> None:
    """Keep real test purposes even when their action cell omits the word unit."""
    argv = [sys.executable, "-m", "pytest", "tests/test_one.py", "--ignore=tests/integration/e2e"]
    _project(tmp_path, [(action, shlex.join(argv)), ("Integration / E2E", "Not applicable")])
    unit = suite_binding(tmp_path, FEATURE, "unit")
    # @spec AC-007: Explicit generic execution binds every declared test command.
    # — .specs/features/078-requirement-evidence-integrity/spec.md#ac-007
    assert unit.get("commands") == [["pytest", ".", *argv[3:]]]
    assert suite_binding(tmp_path, FEATURE, "all")["commands"] == unit["commands"]
    assert not resolve_applicability(tmp_path, FEATURE, "integration-command")["applicable"]
    assert not resolve_applicability(tmp_path, FEATURE, "e2e-command")["applicable"]


def test_quality_actions_precede_purpose_aliases_and_ambiguous_actions_stay_required(
    tmp_path: Path,
) -> None:
    """Neither quality checks nor command arguments silently declare a test suite."""
    command = shlex.join([sys.executable, "-m", "pytest", "tests/test_one.py"])
    feature = _project(
        tmp_path,
        [
            ("Focused behavior", command),
            ("Focused lint regression", "ruff check ."),
            ("Formatting regression", "ruff format --check ."),
            ("Types", "mypy ."),
            ("Integration / E2E", "Not applicable"),
        ],
    )
    assert len(suite_binding(tmp_path, FEATURE, "all").get("commands", [])) == 1
    plan = feature / "plan.md"
    plan.write_text(plan.read_text() + "| Validation | custom-driver run |\n")
    assert "error" in suite_binding(tmp_path, FEATURE, "all")
    assert resolve_applicability(tmp_path, FEATURE, "integration-command")["applicable"]
    assert resolve_applicability(tmp_path, FEATURE, "e2e-command")["applicable"]


def test_opaque_identity_preserves_exact_argv_and_cwd_without_relaxing_known_errors(
    tmp_path: Path,
) -> None:
    """Unknown command identity is distinct from support for assertion certification."""
    nested = tmp_path / "nested"
    nested.mkdir()
    argv = ["npx", "playwright", "test", "--grep", "exact name"]
    # @spec AC-010: Unsupported drivers retain identity, not an invented adapter.
    # — .specs/features/078-requirement-evidence-integrity/spec.md#ac-010
    assert _command_key(tmp_path, argv, nested) == ["opaque", "nested", *argv]
    assert _command_key(tmp_path, ["uv", "run", "pytest"], tmp_path) == [
        "opaque",
        ".",
        "uv",
        "run",
        "pytest",
    ]
    with pytest.raises(ValueError, match="suite_npm_arguments"):
        _command_key(tmp_path, ["npm", "run", "test", "--", "selection"], tmp_path)
    with pytest.raises(ValueError, match="suite_direct_vitest"):
        _command_key(tmp_path, ["vitest", "run"], tmp_path)


def _archive_errors(
    contract: dict[str, Any], task: dict[str, Any], root: Path, receipt: Path
) -> list[str]:
    """Challenge the real policy2 archive guard with one unsupported completed task."""
    artifact = {
        "evidence_policy_version": "2",
        "evidence_contract": contract,
        "goal_hash": contract["goal_hash"],
        "feature": FEATURE,
        "flags": contract["normalized_flags"],
        "command": "spec-test",
        "goal": {
            "tasks": [{"id": t["id"], "status": "pending"} for t in contract["tasks"] if t != task]
            + [
                {
                    "id": task["id"],
                    "status": "complete",
                    "accepted_evidence": {"execution_receipt_path": str(receipt)},
                }
            ]
        },
    }
    return archived_policy2_evidence_errors(artifact, root)


def _declared_drivers(root: Path) -> tuple[list[str], list[str]]:
    """Prepare genuine local Python commands alongside unsupported custom execution."""
    unit = [sys.executable, "-m", "pytest", "tests/test_one.py", "-q"]
    custom = [
        sys.executable,
        "-c",
        "from pathlib import Path; Path('.specs/.execution/custom-ran').write_text('real')",
    ]
    _project(
        root,
        [
            ("Focused behavior", shlex.join(unit)),
            ("E2E", shlex.join(custom)),
            ("Integration", "Not applicable"),
        ],
    )
    return unit, custom


def _goal(root: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compile the real canonical Test goal with its independent final acceptance task."""
    monkeypatch.setattr("validator.hook_resolver.GLOBAL_HOOKS_DIR", root / "absent-hooks")
    goal = compile_command_goal(
        "spec-test",
        project_root=root,
        livespec_root=ROOT,
        feature=FEATURE,
        flags="--auto --no-generate --model=reviewer/v1",
    )
    return json.loads(render_goal_contract_file(goal)), json.loads(render_goal_state_file(goal))


@pytest.mark.integration
def test_custom_command_executes_without_fabricating_assertion_certification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The actual custom program remains executable and its missing proof remains a gap."""
    _, custom = _declared_drivers(tmp_path)
    contract, state = _goal(tmp_path, monkeypatch)
    result = capture_execution(
        custom,
        project_root=tmp_path,
        feature=FEATURE,
        adapter="junit",
        env=dict(os.environ),
        timeout=5,
    )
    # @spec AC-010: A genuine custom driver executes even without an assertion adapter.
    # — .specs/features/078-requirement-evidence-integrity/spec.md#ac-010
    assert (tmp_path / ".specs/.execution/custom-ran").read_text() == "real"
    assert result.exit_code == 0 and result.receipt_path
    receipt = Path(result.receipt_path)
    rejected = verify_execution_observation(receipt, tmp_path, FEATURE, "passed")
    assert not rejected.valid and rejected.certified_acs == []
    e2e = next(
        t
        for t in contract["tasks"]
        if t.get("expected_evidence", {}).get("suite_binding", {}).get("suite") == "e2e"
    )
    assert e2e["expected_evidence"]["suite_binding"].get("commands") == [["opaque", ".", *custom]]
    proof = prove_goal_task(
        contract, state, e2e["id"], {"execution_receipt_path": str(receipt)}, project_root=tmp_path
    )
    assert not proof["accepted"]
    assert "suite_assertion_adapter_unsupported" in " ".join(proof["missing_evidence"])


@pytest.mark.integration
def test_real_unlabelled_unit_cannot_prove_opaque_e2e_or_aggregate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A genuine unit observation cannot stand in for a different command or final acceptance."""
    unit, _ = _declared_drivers(tmp_path)
    contract, state = _goal(tmp_path, monkeypatch)
    captured = capture_execution(
        unit,
        project_root=tmp_path,
        feature=FEATURE,
        adapter="junit",
        env=dict(os.environ),
        timeout=5,
    )
    receipt = Path(captured.receipt_path)
    assert verify_execution_observation(receipt, tmp_path, FEATURE, "passed").valid
    tasks = {
        t["expected_evidence"]["suite_binding"]["suite"]: t
        for t in contract["tasks"]
        if "suite_binding" in t.get("expected_evidence", {})
    }
    evidence = {"execution_receipt_path": str(receipt)}
    # @spec AC-007: A real unlabelled unit proves only its frozen original selection.
    # — .specs/features/078-requirement-evidence-integrity/spec.md#ac-007
    assert prove_goal_task(contract, state, tasks["unit"]["id"], evidence, project_root=tmp_path)[
        "accepted"
    ]
    for suite in ("e2e", "all"):
        proof = prove_goal_task(
            contract, state, tasks[suite]["id"], evidence, project_root=tmp_path
        )
        # @spec AC-009: A genuine passed unit cannot replace another command's proof.
        # — .specs/features/078-requirement-evidence-integrity/spec.md#ac-009
        assert not proof["accepted"]
        assert "suite_assertion_adapter_unsupported" in " ".join(proof["missing_evidence"])
    assert "suite_assertion_adapter_unsupported" in " ".join(
        _archive_errors(contract, tasks["e2e"], tmp_path, receipt)
    )
    acceptance = next(t for t in contract["tasks"] if t.get("acceptance_scope") == "feature")
    assert not prove_goal_task(contract, state, acceptance["id"], evidence, project_root=tmp_path)[
        "accepted"
    ]


def test_consumer_preparation_rows_never_enter_dashboard_slides_test_binding(
    tmp_path: Path,
) -> None:
    """Representative consumer actions exclude installation/build/static preparation."""
    for name in ("dashboard", "slides"):
        (tmp_path / name).mkdir()
    command = shlex.join([sys.executable, "-m", "pytest", "../tests/test_one.py", "-q"])
    _project(
        tmp_path,
        [
            ("Dashboard install", "npm ci (dashboard)"),
            ("Dashboard type check", "npm run check (dashboard)"),
            ("Dashboard unit", command + " (dashboard)"),
            ("Dashboard build", "npm run build (dashboard)"),
            ("Slides install", "npm ci (slides)"),
            ("Slides type check", "npm run check (slides)"),
            ("Slides unit", command + " (slides)"),
            ("Workflow lint", "actionlint .github/workflows/ci.yaml (root)"),
            ("Bootstrap", "npm ci"),
            ("Package generation", "npm run generate"),
            ("Integration / E2E / visual / Python / full suite", "Not run"),
        ],
    )
    binding = suite_binding(tmp_path, FEATURE, "all")
    assert binding.get("commands") == [
        ["pytest", "dashboard", "../tests/test_one.py", "-q"],
        ["pytest", "slides", "../tests/test_one.py", "-q"],
    ]
    assert not resolve_applicability(tmp_path, FEATURE, "e2e-command")["applicable"]


@pytest.mark.parametrize(
    "action,suite",
    [("Unit build tests", "unit"), ("Integration installation tests", "integration")],
)
def test_explicit_suite_labels_override_non_test_vocabulary(
    tmp_path: Path,
    action: str,
    suite: str,
) -> None:
    """An explicit suite cannot disappear because its tests concern build/install behavior."""
    argv = [sys.executable, "-m", "pytest", "tests/test_one.py"]
    _project(tmp_path, [(action, shlex.join(argv))])
    assert suite_binding(tmp_path, FEATURE, suite).get("commands") == [["pytest", ".", *argv[3:]]]
