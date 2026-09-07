"""Fix commands require current readiness and prove only their actual execution scope."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.review_support import reviewed_project
from validator.cli import app
from validator.evidence_policy import typed_evidence_missing
from validator.goal_contracts import compile_command_goal

ROOT = Path(__file__).parents[1]
SKILL = ROOT / ".agent-sync/skills/spec-fix/SKILL.md"


@pytest.mark.parametrize(
    "flags", ["", "--resume", "--ac AC-001", "--fr FR-001", "--visual", "--functional"]
)
def test_fix_test_execution_cannot_be_proven_with_prose(tmp_path: Path, flags: str) -> None:
    feature = reviewed_project(tmp_path)
    with (feature / "spec.md").open("a") as source:
        source.write(
            "\n## Functional Requirements\n| ID | Requirement | AC |\n|---|---|---|\n"
            "| FR-001 | Delete expired files | AC-001 |\n"
            "## Acceptance Criteria\n| ID | Criterion |\n|---|---|\n"
            "| AC-001 | Expired files are absent |\n"
        )
    goal = compile_command_goal(
        "spec-fix", project_root=tmp_path, livespec_root=ROOT, feature="001-test", flags=flags
    )
    tasks = [task for task in goal.payload["tasks"] if task["evidence_kind"] == "execution"]
    assert tasks
    for task in tasks:
        assert typed_evidence_missing(
            task,
            {"output": "All tests passed", "success_criteria_met": True},
            contract=goal.payload,
            project_root=tmp_path,
        ) == ["execution_receipt_path"]
    full = [task for task in tasks if task.get("acceptance_scope") == "feature"]
    assert bool(full) == (flags in {"", "--resume"})


@pytest.mark.parametrize("flags", ["--dry-run", "--conventions", "--audit-only", "--all"])
def test_fix_non_feature_execution_modes_add_no_feature_certificate(
    tmp_path: Path, flags: str
) -> None:
    reviewed_project(tmp_path)
    goal = compile_command_goal(
        "spec-fix",
        project_root=tmp_path,
        livespec_root=ROOT,
        feature=None if flags == "--all" else "001-test",
        flags=flags,
    )
    assert not [task for task in goal.payload["tasks"] if task["evidence_kind"] == "execution"]


def test_fix_readiness_precedes_mutation_and_forwards_review_identity() -> None:
    text = SKILL.read_text()
    phase = text.split("### Step 6 — Execute Fixes", 1)[1].split("### Step 7", 1)[0]
    assert phase.index("--progression implement") < phase.index("**Functional fixes:**")
    assert "--model <resolved-model>" in phase
    assert "--review-max-chars <resolved-budget>" in phase
    invocations = text.split("## Internal Command Invocations", 1)[1].split("## ", 1)[0]
    assert invocations.count("same model and review budget") == 3


def test_fix_uses_existing_gate_that_rejects_missing_and_stale_reviews(tmp_path: Path) -> None:
    feature = reviewed_project(tmp_path)
    command = ["validate", str(feature), "--progression", "implement", "--model", "reviewer/v1"]
    runner = CliRunner()
    assert runner.invoke(app, command).exit_code == 0
    (feature / ".reviews/spec.json").unlink()
    missing = runner.invoke(app, command)
    assert missing.exit_code == 1
    assert "clarify_not_ready" in missing.output
    reviewed_project(tmp_path)
    (feature / "plan.md").write_text("# Plan\nKeep files forever.\n")
    stale = runner.invoke(app, command)
    assert stale.exit_code == 1
    assert "analyze_not_ready" in stale.output


def test_collection_delegates_repairs_to_typed_feature_contracts(tmp_path: Path) -> None:
    reviewed_project(tmp_path)
    text = SKILL.read_text()
    collection = text.split("## Multi-Feature Mode", 1)[1].split("## Edge Cases", 1)[0]
    assert "independent `/spec-fix <feature>` child" in collection
    assert "removing `--all`/`-A`" in collection
    batch = compile_command_goal(
        "spec-fix", project_root=tmp_path, livespec_root=ROOT, flags="--all --ac AC-001"
    )
    child = compile_command_goal(
        "spec-fix",
        project_root=tmp_path,
        livespec_root=ROOT,
        feature="001-test",
        flags="--ac AC-001",
    )
    assert not any(t["evidence_kind"] == "execution" for t in batch.payload["tasks"])
    assert any(t["evidence_kind"] == "execution" for t in child.payload["tasks"])
    assert not any(t.get("acceptance_scope") == "feature" for t in child.payload["tasks"])


def test_test_preview_flags_do_not_weaken_other_command_execution(tmp_path: Path) -> None:
    reviewed_project(tmp_path)
    goal = compile_command_goal(
        "spec-implement",
        project_root=tmp_path,
        livespec_root=ROOT,
        feature="001-test",
        flags="--dry-run --regenerate-missing",
    )
    assert any(t["evidence_kind"] == "execution" for t in goal.payload["tasks"])
