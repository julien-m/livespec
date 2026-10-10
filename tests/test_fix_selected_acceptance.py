"""Filtered repairs cannot substitute another accepted execution or mutate during previews."""

import json
import re
import shlex
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.execution_evidence_support import FEATURE, _review_response, run
from tests.execution_evidence_support import project as project
from validator.cli import app
from validator.evidence_policy import typed_evidence_missing
from validator.execution_mapping import ingest_mapping_review, prepare_mapping_review
from validator.goal_contracts import compile_command_goal

ROOT = Path(__file__).parents[1]


def _declare_filters(root: Path) -> None:
    spec = root / ".specs/features" / FEATURE / "spec.md"
    spec.write_text(
        "# Addition\nAC-001: Adding one and two returns three.\n"
        "## Functional Requirements\n| ID | Requirement | ACs |\n|---|---|---|\n"
        "| FR-001 | Addition | AC-001 |\n| FR-002 | Subtraction | AC-002 |\n"
        "## Acceptance Criteria\n| ID | Criterion |\n|---|---|\n"
        "| AC-001 | Adding one and two returns three. |\n"
        "| AC-002 | Subtracting one from two returns one. |\n"
    )
    _refresh_mapping(root)


def _refresh_mapping(root: Path) -> None:
    prepared = prepare_mapping_review(root, FEATURE, root / "mapping.json")
    raw = json.loads(_review_response(prepared))
    citation = raw["conclusions"][0]["source_citations"][0]
    citation["section_id"] = next(
        section.section_id
        for section in prepared.sections
        if section.role == "spec" and citation["excerpt"] in section.text
    )
    receipt = ingest_mapping_review(prepared, [json.dumps(raw)], root / "acceptance-review.json")
    assert receipt.ready, receipt.errors


@pytest.mark.parametrize("flag", ["--ac AC-002", "--fr FR-002"])
def test_selected_fix_rejects_real_receipt_for_another_acceptance(project: Path, flag: str) -> None:
    _declare_filters(project)
    receipt = run(project)
    goal = compile_command_goal(
        "spec-fix", project_root=project, livespec_root=ROOT, feature=FEATURE, flags=flag
    )
    tasks = [t for t in goal.payload["tasks"] if t["evidence_kind"] == "execution"]
    assert tasks
    for task in tasks:
        missing = typed_evidence_missing(
            task,
            {"execution_receipt_path": str(receipt)},
            contract=goal.payload,
            project_root=project,
        )
        assert missing, "AC-001 passed, but the requested AC-002 was not executed"


@pytest.mark.parametrize(
    "flag", ["--ac AC-999", "--fr FR-999", "--ac", "--fr", "--ac AC-001 --fr FR-001"]
)
def test_unknown_or_missing_filter_cannot_compile(project: Path, flag: str) -> None:
    _declare_filters(project)
    with pytest.raises(ValueError):
        compile_command_goal(
            "spec-fix", project_root=project, livespec_root=ROOT, feature=FEATURE, flags=flag
        )


@pytest.mark.parametrize("flag", ["--dry-run", "-d", "--all", "-A", "--conventions"])
def test_preview_and_collection_goals_contain_no_feature_writes(project: Path, flag: str) -> None:
    goal = compile_command_goal(
        "spec-fix", project_root=project, livespec_root=ROOT, feature=FEATURE, flags=flag
    )
    descriptions = [task["description"] for task in goal.payload["tasks"]]
    forbidden = (
        "Execute functional fixes",
        "Generate tests for new AC",
        "Update progress.md",
        "Write feature changelog",
        "Write global",
        "Finalize registry",
        "new mappings",
    )
    assert not [text for text in descriptions if any(item in text for item in forbidden)]


def test_documented_fix_runner_invocation_executes_real_tests(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(project)
    text = (ROOT / ".agent-sync/skills/spec-fix/SKILL.md").read_text()
    command = re.search(r"`(livespec test [^`]+)`", text)
    assert command is not None
    argv = command[1].replace("<feature>", FEATURE).replace("<mapping-path>", "mapping.json")
    argv = argv.replace("<resolved-command>", f"{sys.executable} -m pytest test_app.py -q")
    result = CliRunner().invoke(app, shlex.split(argv)[1:])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["execution_receipt_path"]


@pytest.mark.parametrize("flag", ["--ac AC-001", "--fr FR-001"])
def test_selected_fix_accepts_matching_real_execution_and_lifecycle_update(
    project: Path, flag: str
) -> None:
    _declare_filters(project)
    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text("---\nstatus: Approved\n---\n" + spec.read_text())
    _refresh_mapping(project)
    receipt = run(project)
    goal = compile_command_goal(
        "spec-fix", project_root=project, livespec_root=ROOT, feature=FEATURE, flags=flag
    )
    spec.write_text(spec.read_text().replace("status: Approved", "status: Implemented"))
    for task in goal.payload["tasks"]:
        if task["evidence_kind"] == "execution":
            assert task["required_acs"] == [f"{FEATURE}:AC-001"]
            assert not typed_evidence_missing(
                task,
                {"execution_receipt_path": str(receipt)},
                contract=goal.payload,
                project_root=project,
            )


def test_changed_fr_mapping_rejects_even_a_fresh_real_capture(project: Path) -> None:
    _declare_filters(project)
    goal = compile_command_goal(
        "spec-fix", project_root=project, livespec_root=ROOT, feature=FEATURE, flags="--fr FR-001"
    )
    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text(
        spec.read_text().replace("| FR-001 | Addition | AC-001 |", "| FR-001 | Addition | AC-002 |")
    )
    _refresh_mapping(project)
    receipt = run(project)
    task = next(t for t in goal.payload["tasks"] if t["evidence_kind"] == "execution")
    assert typed_evidence_missing(
        task, {"execution_receipt_path": str(receipt)}, contract=goal.payload, project_root=project
    ) == ["fix_acceptance_selection_changed_recompile_required"]


@pytest.mark.parametrize("replacement", ["", "AC-999"])
def test_missing_or_dangling_fr_acceptance_mapping_blocks(project: Path, replacement: str) -> None:
    _declare_filters(project)
    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text(
        spec.read_text().replace(
            "| FR-002 | Subtraction | AC-002 |", f"| FR-002 | Subtraction | {replacement} |"
        )
    )
    with pytest.raises(ValueError):
        compile_command_goal(
            "spec-fix",
            project_root=project,
            livespec_root=ROOT,
            feature=FEATURE,
            flags="--fr FR-002",
        )


def test_documentary_acceptance_cannot_be_certified_by_filtered_runtime(project: Path) -> None:
    _declare_filters(project)
    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text(
        spec.read_text() + "\n### AC-003\nReview source.\n**Evidence:** review\n"
        "**Review inputs:** [source](../../../app.py)\n"
    )
    with pytest.raises(ValueError, match="full_feature_verification"):
        compile_command_goal(
            "spec-fix",
            project_root=project,
            livespec_root=ROOT,
            feature=FEATURE,
            flags="--ac AC-003",
        )
