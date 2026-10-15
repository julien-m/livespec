"""Release evidence: pending in the implement goal, required by the ship progression (090)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tests.plan_evidence_support import MODEL, RELEASE_PLAN, plan_text, write_plan
from tests.stable_review_support import FEATURE, make_root, review_both
from validator.cli import app
from validator.progression_gate import ProgressionBlocked, require_progression
from validator.release_evidence import release_evidence, release_goal_context

PROOF = "| 2 | Signed build | notarized build 1.4 (receipt.json) |"


def _implementation(root: Path, rows: str, heading: str = "## Release Evidence") -> None:
    table = f"{heading}\n\n| Step | Evidence | Proof |\n|---|---|---|\n{rows}\n"
    (root / ".specs/features" / FEATURE / "implementation.md").write_text(table)


def _feature(tmp_path: Path) -> Path:
    feature = tmp_path / ".specs/features" / FEATURE
    feature.mkdir(parents=True)
    (feature / "plan.md").write_text(RELEASE_PLAN)
    return tmp_path


# @spec AC-002: Release evidence pending, satisfied once recorded
#   — .specs/features/090-minimal-plan-scope/spec.md#ac-002
def test_release_evidence_is_pending_until_recorded(tmp_path: Path) -> None:
    root = _feature(tmp_path)
    [item] = release_evidence(root, FEATURE)
    assert item == {
        "feature": FEATURE,
        "step": "2",
        "evidence": "Step 2 — Signed build",
        "status": "pending",
    }
    _implementation(
        root, "| 1 | Purge job | not a release step |\n" + PROOF.replace("2", "Step 02", 1)
    )
    [item] = release_evidence(root, FEATURE)
    assert item["status"] == "satisfied"
    assert item["proof"] == "notarized build 1.4 (receipt.json)"


@pytest.mark.parametrize(
    "proof",
    [
        "pending",
        "pending notarization",
        "not yet produced",
        "\u2014",
        "?",
        "TBC",
        "will be signed later",
        "_pending_",
        "[ ]",
        "no proof yet",
        "blocked",
        "not done",
        "x",
        "\u23f3 Pending notarization",
        "\u274c Not produced",
        "(pending)",
        "<receipt path>",
    ],
)
def test_announced_proof_keeps_release_pending(tmp_path: Path, proof: str) -> None:
    root = _feature(tmp_path)
    _implementation(root, f"| 2 | Signed build | {proof} |")
    assert release_evidence(root, FEATURE)[0]["status"] == "pending"


@pytest.mark.parametrize(
    ("rows", "heading"),
    [
        (PROOF + "\n| 2 | Signed build | pending |", "## Release Evidence"),
        (f"```markdown\n{PROOF}\n```", "## Release Evidence"),
        (f"<!--\n{PROOF}\n-->", "## Release Evidence"),
        ("    " + PROOF, "## Release Evidence"),
        (PROOF, "## Release Evidence (template)"),
    ],
)
def test_example_or_withdrawn_proof_keeps_release_pending(
    tmp_path: Path, rows: str, heading: str
) -> None:
    root = _feature(tmp_path)
    _implementation(root, rows, heading)
    assert release_evidence(root, FEATURE)[0]["status"] == "pending"


@pytest.mark.parametrize("row", ["| 2 | Device fleet run | notarized |", "| 2 | notarized |"])
def test_proof_naming_another_step_is_a_mismatch(tmp_path: Path, row: str) -> None:
    root = _feature(tmp_path)
    _implementation(root, row)
    assert release_evidence(root, FEATURE)[0]["status"] == "mismatch"


def _goal() -> dict[str, Any]:
    args = ["goal", "render", "spec-implement", "--feature", FEATURE]
    result = CliRunner().invoke(app, [*args, "--flags", f"--model={MODEL}", "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)["canonical"]


# @spec AC-002: Release evidence never blocks finalize (SC-001)
#   — .specs/features/090-minimal-plan-scope/spec.md#ac-002
def test_implement_goal_lists_release_evidence_outside_required_tasks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_root(tmp_path)
    monkeypatch.chdir(root)
    before = _goal()
    assert "pending_release_evidence" not in before["runtime_context"]
    write_plan(root, RELEASE_PLAN)
    (root / ".specs/features" / FEATURE / "implementation.md").write_bytes(b"\xff\xfe broken")
    goal = _goal()
    assert goal["runtime_context"]["pending_release_evidence"][0]["step"] == "2"
    _implementation(root, PROOF)
    assert "pending_release_evidence" not in _goal()["runtime_context"]
    _implementation(root, "| 2 | Signed build | pending |")
    goal = _goal()
    pending = goal["runtime_context"]["pending_release_evidence"]
    assert [item["step"] for item in pending] == ["2"]
    # The required tasks are those of a plan without release evidence: nothing blocks finalize.
    assert [t["id"] for t in goal["tasks"]] == [t["id"] for t in before["tasks"]]


def _ship(root: Path) -> None:
    require_progression(root, FEATURE, "ship", model=MODEL)


# @spec AC-002: spec-ship requires release evidence
#   — .specs/features/090-minimal-plan-scope/spec.md#ac-002
def test_ship_progression_requires_recorded_release_evidence(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    _ship(root)  # No release step: ship is the complete progression.
    write_plan(root, RELEASE_PLAN)
    review_both(root)
    require_progression(root, FEATURE, "complete", model=MODEL)
    with pytest.raises(ProgressionBlocked, match="release_evidence_pending:step 2: Step 2"):
        _ship(root)
    _implementation(root, "| 2 | Signed build | \u23f3 pending notarization |")
    with pytest.raises(ProgressionBlocked, match="release_evidence_pending"):
        _ship(root)
    _implementation(root, "| 2 | Device fleet run | notarized build 1.4 |")
    with pytest.raises(ProgressionBlocked, match="release_evidence_invalid:Release Evidence row"):
        _ship(root)
    _implementation(root, PROOF)
    _ship(root)


def test_ship_progression_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_root(tmp_path)
    write_plan(root, RELEASE_PLAN)
    review_both(root)
    monkeypatch.chdir(root)
    feature = root / ".specs/features" / FEATURE
    args = ["validate", str(feature), "--progression", "ship", "--model", MODEL]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 1
    assert "release_evidence_pending" in result.output


@pytest.mark.parametrize(
    "declaration",
    [
        "**Evidence class:** release (signing)",
        "**Evidence class:** release\n**Evidence class:** release",
        "| x | **Evidence class:** release |",
    ],
)
def test_ship_fails_closed_on_an_invalid_plan(tmp_path: Path, declaration: str) -> None:
    root = make_root(tmp_path)
    write_plan(root, plan_text(f"### Step 1 — Sign\n\n{declaration}\n"))
    review_both(root)
    with pytest.raises(ProgressionBlocked, match="release_evidence_invalid"):
        _ship(root)


def test_release_line_outside_the_plan_section_fails_closed(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    write_plan(root, "# Plan\n\n## Steps\n\n### Step 1 — Sign\n\n**Evidence class:** release\n")
    review_both(root)
    with pytest.raises(ProgressionBlocked, match="release_evidence_invalid"):
        _ship(root)


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads unreadable files")
def test_unreadable_map_is_reported_not_raised(tmp_path: Path) -> None:
    root = _feature(tmp_path)
    _implementation(root, PROOF)
    implementation = root / ".specs/features" / FEATURE / "implementation.md"
    implementation.chmod(0)
    try:
        context = release_goal_context("spec-implement", root, FEATURE)
    finally:
        implementation.chmod(0o644)
    assert "PermissionError" in str(context["release_evidence_unreadable"])
