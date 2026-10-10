"""Visual-only goals retain visual proof without inventing a functional suite result."""

from pathlib import Path

import pytest

from tests.test_command_preview_obligations import ROOT, _goal


@pytest.mark.parametrize("flags,suite_active", [("", True), ("--visual", False)])
def test_visual_prerequisite_distinguishes_failed_suite_from_unrequested_suite(
    tmp_path: Path, flags: str, suite_active: bool
) -> None:
    tasks = _goal(tmp_path, "spec-test", flags, True).payload["tasks"]
    suite = [task for task in tasks if task["description"] == "Full test suite executed"]
    assert bool(suite) is suite_active
    if suite:
        assert suite[0]["required_evidence"] == ["execution_receipt_path"]
    guard = next(task for task in tasks if "Skip phase 4.5" in task["description"])
    assert "only if `test-suite` is active and Phase 4 failed" in guard["description"]
    assert "non-zero exit code" in guard["description"]
    assert "`--visual`" in guard["description"] and "`not_run`" in guard["description"]
    assert (
        "proceed" in guard["description"] and "never claim full-suite PASS" in guard["description"]
    )
    dispatcher = next(
        task for task in tasks if "Select dispatcher based on surfaces.yaml" in task["description"]
    )
    gate = next(task for task in tasks if task["id"] == "visual.gate_validate")
    assert guard["ordinal"] < dispatcher["ordinal"] < gate["ordinal"]
    assert "--receipt <receipt-path>" in gate["description"]
    assert "verbal_visual_confirmation_without_artifact" in gate["invalid_substitutes"]


def test_capture_prose_requires_only_an_applicable_functional_suite(tmp_path: Path) -> None:
    _goal(tmp_path, "spec-test", "--visual", True)
    skill = (ROOT / ".agent-sync/skills/spec-test/SKILL.md").read_text()
    prerequisite = skill.split("### 4.5.2 — Capture Baselines", 1)[1].split("**CRITICAL", 1)[0]
    assert "If `test-suite` is active" in prerequisite
    assert "non-zero exit code" in prerequisite
    assert "`not_run`" in prerequisite and "never claim full-suite PASS" in prerequisite
    assert "proceed" in prerequisite


@pytest.mark.parametrize("flags", ["--visual --dry-run", "--regenerate-missing --confirm"])
def test_inactive_visual_modes_have_no_capture_prerequisite_or_visual_receipt_task(
    tmp_path: Path, flags: str
) -> None:
    tasks = _goal(tmp_path, "spec-test", flags, True).payload["tasks"]
    assert not any("Skip phase 4.5" in task["description"] for task in tasks)
    assert not any(task["id"].startswith("visual.gate_validate") for task in tasks)
    assert not any("After runtime capture and approval" in task["description"] for task in tasks)
    assert not any(task["description"] == "Full test suite executed" for task in tasks)
