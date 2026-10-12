# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-002)
# @spec(AC-003)
# @spec(AC-009)
# @spec(AC-010)

"""Command-contract tests for the Design Alignment Gate."""

from __future__ import annotations

from pathlib import Path

from validator.expectations import parse_expectations

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_global_workflow_docs_exist_and_capture_cloudskill_rules() -> None:
    workflow = _read("system/testing/design-alignment.md")
    quality = _read("system/testing/design-alignment-quality.md")
    schema = _read("system/schemas/design-alignment-manifest.md")

    assert "Mockup-Code Alignment" in workflow
    assert "Design Alignment Verdict: PASS | FAIL | BLOCKED" in workflow
    assert "SUPPORT_MATCH" in workflow
    assert "same frame size" in quality
    assert "safe-area" in quality
    assert "design_hash" in schema
    assert "runtime_hash" in schema


def test_spec_test_documents_design_alignment_before_baseline_capture() -> None:
    body = _read(".agent-sync/skills/spec-test/SKILL.md")

    assert "### 4.5.0 — Design Alignment Gate" in body
    assert "system/testing/design-alignment.md" in body
    assert "Design Alignment Verdict: PASS | FAIL | BLOCKED" in body
    assert "FAIL` or `BLOCKED` prevents baseline capture" in body


def test_test_expectations_require_design_alignment_for_visual_runs() -> None:
    parsed = parse_expectations(ROOT / ".agent-sync/skills/spec-test/expectations.md")
    visual = [branch for branch in parsed.verify.when if branch.flag == "--visual"]

    # The verdict only appears when ui.pen exists, so the machine rule is a --visual "may".
    assert len(visual) == 1
    assert ("contains", "Design Alignment Verdict") in [
        (rule.kind, rule.payload) for rule in visual[0].may
    ]
    filesystem = parsed.prose_sections["4. Filesystem Effects"]
    assert ".specs/features/<feature>/design-alignment/" in filesystem
