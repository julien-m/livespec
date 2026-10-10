"""Actual scoped/repo gate regressions: identity, verdict and changed source."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.test_conventions_final_tasks import _goal, _read_apply
from tests.test_conventions_verify_scope import _write_feature_scope
from validator.cli import app
from validator.cli_commands import conventions_cmd
from validator.conventions_gate_types import GateBlocker, GateResult, GateVerdict, GateViolation
from validator.conventions_gates import gates_path
from validator.conventions_receipt import verify_conventions_receipt, write_conventions_receipt
from validator.goal_contracts import prove_goal_task
from validator.run_receipts import verify_one_receipt

FEATURE = "001-demo"


def _final_fixture(tmp_path: Path):
    project, contract, state = _goal(tmp_path, "spec-fix")
    source = project / "src/scoped.py"
    source.parent.mkdir()
    source.write_text('"""Scoped source."""\n')
    _write_feature_scope(project, FEATURE, ["src/scoped.py"])
    evidence = _read_apply()
    for identity, key in [
        (FEATURE, "conventions_receipt_path"),
        ("repo", "repo_conventions_receipt_path"),
    ]:
        result = CliRunner().invoke(
            app,
            [
                "conventions",
                "verify",
                "--repo",
                str(project),
                "--feature",
                identity,
                "--run-id",
                identity,
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        evidence[key] = json.loads(result.output)["receipt_path"]
    task = next(
        task
        for task in contract["tasks"]
        if "repo_conventions_receipt_path" in task["required_evidence"]
    )
    return project, contract, state, task, evidence


def test_ac005_final_two_genuine_scope_pass_receipts_accept(tmp_path: Path) -> None:
    project, contract, state, task, evidence = _final_fixture(tmp_path)
    result = prove_goal_task(contract, state, task["id"], evidence, project_root=project)
    assert result["accepted"] is True


@pytest.mark.parametrize("key", ["conventions_receipt_path", "repo_conventions_receipt_path"])
def test_ac005_final_missing_receipt_rejects(tmp_path: Path, key: str) -> None:
    project, contract, state, task, evidence = _final_fixture(tmp_path)
    del evidence[key]
    result = prove_goal_task(contract, state, task["id"], evidence, project_root=project)
    assert result["accepted"] is False
    assert key in result["missing_evidence"]


def test_ac007_feature_pass_cannot_substitute_for_repo(tmp_path: Path) -> None:
    project, contract, state, task, evidence = _final_fixture(tmp_path)
    evidence["repo_conventions_receipt_path"] = evidence["conventions_receipt_path"]
    result = prove_goal_task(contract, state, task["id"], evidence, project_root=project)
    assert result["accepted"] is False
    assert "repo_conventions_receipt_path_valid:feature_slug_mismatch" in result["missing_evidence"]


def test_ac007_repo_receipt_path_outside_project_rejects(tmp_path: Path) -> None:
    project, contract, state, task, evidence = _final_fixture(tmp_path)
    evidence["repo_conventions_receipt_path"] = str(tmp_path / "outside-receipt.json")
    result = prove_goal_task(contract, state, task["id"], evidence, project_root=project)
    assert result["accepted"] is False
    assert any(
        "repo_conventions_receipt_path_valid:path_outside_project" in item
        for item in result["missing_evidence"]
    )


@pytest.mark.parametrize("verdict", [GateVerdict.FAIL, GateVerdict.BLOCKED])
def test_ac005_non_pass_repo_receipt_rejects(tmp_path: Path, verdict: GateVerdict) -> None:
    project, contract, state, task, evidence = _final_fixture(tmp_path)
    result = GateResult(
        verdict,
        [GateViolation("length", "src/scoped.py", 1, "error", "too long", "builtin")]
        if verdict == GateVerdict.FAIL
        else [],
        [GateBlocker("tool_missing", "Required tool missing")]
        if verdict == GateVerdict.BLOCKED
        else [],
    )
    path = write_conventions_receipt(
        project_root=project,
        feature_slug="repo",
        run_id="nonpass",
        result=result,
        gates_path=gates_path(project),
    )
    evidence["repo_conventions_receipt_path"] = str(path)
    proof = prove_goal_task(contract, state, task["id"], evidence, project_root=project)
    assert proof["accepted"] is False
    assert "repo_conventions_receipt_path_verdict_pass" in proof["missing_evidence"]


@pytest.mark.parametrize("path", ["src/scoped.py", "src/unrelated.py"])
def test_ac015_old_pass_cannot_override_current_source_failure(tmp_path: Path, path: str) -> None:
    project, contract, state, task, evidence = _final_fixture(tmp_path)
    (project / path).write_text('"""Nonconforming source."""\n' + "\n" * 600)
    receipt_path = evidence["repo_conventions_receipt_path"]
    assert isinstance(receipt_path, str)
    assert verify_conventions_receipt(Path(receipt_path), project_root=project).verdict == "PASS"
    proof = prove_goal_task(contract, state, task["id"], evidence, project_root=project)
    assert proof["accepted"] is False
    assert "conventions_current_verdict_pass:repo:FAIL" in proof["missing_evidence"]
    check = verify_one_receipt(
        kind="conventions_repo", path=receipt_path, project_root=project, feature=FEATURE
    )
    assert check.verified is True
    assert check.verdict == "FAIL"


def test_ac015_final_rerun_keeps_cli_only_registry_blockers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, contract, state, task, evidence = _final_fixture(tmp_path)

    def block_registry(result: GateResult, repo_root: Path) -> GateResult:
        assert repo_root == project
        assert result.verdict == GateVerdict.PASS
        return GateResult(
            GateVerdict.BLOCKED,
            [],
            [GateBlocker("rule_decision_manifest_invalid", "Invalid registry")],
        )

    monkeypatch.setattr(conventions_cmd, "_with_rule_decision_blockers", block_registry)
    result = prove_goal_task(contract, state, task["id"], evidence, project_root=project)
    assert result["accepted"] is False
    assert "conventions_current_verdict_pass:repo:BLOCKED" in result["missing_evidence"]
