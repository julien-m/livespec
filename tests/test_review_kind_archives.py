"""Canonical review purposes survive prove, archive and later receipt-mirror edits."""

import hashlib
import json
from pathlib import Path

import pytest

from tests.test_goal_review_roundtrip import review_goal_files as review_goal_files
from validator.cli import app
from validator.goal_contracts import compile_command_goal


def _historical_contract(contract, state, policy):
    """Recreate the exact pre-kind canonical shape with a consistent historical hash."""
    document = json.loads(contract.read_text())
    canonical = document["canonical"]
    canonical["evidence_policy_version"] = policy
    for task in canonical["tasks"]:
        task.get("expected_evidence", {}).pop("review_kind", None)
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    document.update(canonical=canonical, canonical_json=raw, tasks=canonical["tasks"])
    document.update(
        goal_hash=hashlib.sha256(raw.encode()).hexdigest(), evidence_policy_version=policy
    )
    snapshot = json.loads(state.read_text())
    snapshot["goal_hash"] = document["goal_hash"]
    contract.write_text(json.dumps(document))
    state.write_text(json.dumps(snapshot))
    return document


def _complete_and_archive(root, files, *, supplied="plan"):
    runner, _, contract, _, common = files
    document = json.loads(contract.read_text())
    for task in document["tasks"]:
        if task["id"] == "archive.run":
            continue
        evidence = {"output": "done", "success_criteria_met": True}
        if task["evidence_kind"] == "review":
            evidence = {
                "review_receipt_path": str(
                    root / f".specs/features/001-test/.reviews/{supplied}.json"
                )
            }
        result = runner.invoke(
            app,
            ["goal", "prove", *common, "--task", task["id"], "--evidence", json.dumps(evidence)],
        )
        assert result.exit_code == 0, result.output
    archive = runner.invoke(app, ["goal", "archive", *common, "--exit-code", "0", "--json"])
    assert archive.exit_code == 0, archive.output
    return Path(json.loads(archive.output)["archived"])


@pytest.mark.parametrize("mutation", ["missing", "replacement", "entry-removed", "entry-kind"])
def test_current_archive_rejects_review_kind_mirror_tampering(
    tmp_path, review_goal_files, mutation
):
    runner, _, _, _, _ = review_goal_files
    path = _complete_and_archive(tmp_path, review_goal_files)
    original = runner.invoke(app, ["verify-output", "spec-demo", "--run", str(path)])
    assert original.exit_code == 0, original.output
    document = json.loads(path.read_text())
    entry = next(row for row in document["receipts"] if row["kind"] == "review")
    assert entry["review_kind"] == "plan"
    if mutation == "missing":
        entry.pop("review_kind")
    elif mutation == "replacement":
        entry["review_kind"] = "spec"
    elif mutation == "entry-kind":
        entry["kind"] = "acceptance_review"
    else:
        document["receipts"].remove(entry)
    path.write_text(json.dumps(document))
    rejected = runner.invoke(app, ["verify-output", "spec-demo", "--run", str(path)])
    assert rejected.exit_code == 1, rejected.output


@pytest.mark.parametrize("policy", ["1", "2"])
@pytest.mark.parametrize("supplied", ["spec", "plan"])
def test_historical_canonical_without_kind_keeps_original_archive_semantics(
    tmp_path, review_goal_files, policy, supplied
):
    runner, _, contract, state, _ = review_goal_files
    historical = _historical_contract(contract, state, policy)
    path = _complete_and_archive(tmp_path, review_goal_files, supplied=supplied)
    document = json.loads(path.read_text())
    assert document["evidence_policy_version"] == policy
    assert all("review_kind" not in entry for entry in document["receipts"])
    verified = runner.invoke(app, ["verify-output", "spec-demo", "--run", str(path)])
    assert verified.exit_code == 0, verified.output
    assert json.loads(contract.read_text()) == historical


def test_new_custom_review_compilation_requires_explicit_kind(tmp_path, review_goal_files):
    _, goal, _, _, _ = review_goal_files
    task = next(task for task in goal.payload["tasks"] if task["evidence_kind"] == "review")
    assert task["expected_evidence"]["review_kind"] == "plan"
    skill = tmp_path / "producer/.agent-sync/skills/spec-demo/SKILL.md"
    skill.write_text(skill.read_text().replace(" review-kind:plan", ""))
    with pytest.raises(ValueError, match="review_kind_required"):
        compile_command_goal(
            "spec-demo",
            project_root=tmp_path,
            livespec_root=tmp_path / "producer",
            feature="001-test",
            flags="--model=reviewer/v1",
        )


@pytest.mark.parametrize("expected,supplied", [("spec", "plan"), ("plan", "spec")])
def test_native_prove_rejects_opposite_kind_and_accepts_declared_review(
    tmp_path, review_goal_files, expected, supplied
):
    from validator.goal_contracts import render_goal_contract_file, render_goal_state_file

    runner, _, contract, state, common = review_goal_files
    skill = tmp_path / "producer/.agent-sync/skills/spec-demo/SKILL.md"
    skill.write_text(skill.read_text().replace("review-kind:plan", f"review-kind:{expected}"))
    goal = compile_command_goal(
        "spec-demo",
        project_root=tmp_path,
        livespec_root=tmp_path / "producer",
        feature="001-test",
        flags="--model=reviewer/v1",
    )
    contract.write_text(render_goal_contract_file(goal))
    state.write_text(render_goal_state_file(goal))
    task = next(task for task in goal.payload["tasks"] if task["evidence_kind"] == "review")
    assert task["expected_evidence"]["review_kind"] == expected
    wrong = {
        "review_receipt_path": str(tmp_path / f".specs/features/001-test/.reviews/{supplied}.json"),
        "review_kind": expected,
    }
    rejected = runner.invoke(
        app, ["goal", "prove", *common, "--task", task["id"], "--evidence", json.dumps(wrong)]
    )
    assert rejected.exit_code == 1, rejected.output
    correct = {
        "review_receipt_path": str(tmp_path / f".specs/features/001-test/.reviews/{expected}.json")
    }
    accepted = runner.invoke(
        app, ["goal", "prove", *common, "--task", task["id"], "--evidence", json.dumps(correct)]
    )
    assert accepted.exit_code == 0, accepted.output


def test_archive_reads_review_kind_from_contract_even_if_state_claims_other_kind(
    tmp_path, review_goal_files
):
    runner, _, _, state, common = review_goal_files
    _complete_and_archive(tmp_path, review_goal_files)
    document = json.loads(state.read_text())
    task = next(
        row
        for row in document["tasks"].values()
        if "review_receipt_path" in (row.get("accepted_evidence") or {})
    )
    task["expected_evidence"] = {"review_kind": "spec"}
    task["accepted_evidence"] = {
        "review_receipt_path": str(tmp_path / ".specs/features/001-test/.reviews/spec.json"),
        "review_kind": "spec",
    }
    state.write_text(json.dumps(document))
    result = runner.invoke(app, ["goal", "archive", *common, "--exit-code", "0", "--json"])
    assert result.exit_code == 1, result.output
    archived = json.loads(Path(json.loads(result.output)["archived"]).read_text())
    check = next(row for row in archived["receipts"] if row["kind"] == "review")
    assert check["review_kind"] == "plan" and check["verified"] is False
