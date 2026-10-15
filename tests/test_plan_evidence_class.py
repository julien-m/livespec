"""Minimal plan scope and plan evidence classes (feature 090)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tests.plan_evidence_support import LIVESPEC_ROOT, MODEL, RELEASE_PLAN, plan_text, write_plan
from tests.review_support import grounded_response
from tests.stable_review_support import FEATURE, make_root
from validator.cli import app
from validator.cli_commands.operation_options import SemanticOptions, check_semantic_options
from validator.plan_evidence import evidence_class_errors, plan_steps
from validator.progression_gate import PROGRESSION_DESTINATIONS
from validator.semantic.review_api import ingest_feature_review
from validator.semantic.review_files import prepare_feature_review


# @spec AC-002: Evidence class per step, default local
#   — .specs/features/090-minimal-plan-scope/spec.md#ac-002
def test_steps_default_to_local_and_read_release() -> None:
    steps, orphans = plan_steps(RELEASE_PLAN)
    assert [(s.label, s.title, s.evidence_class) for s in steps] == [
        ("1", "Step 1 — Purge job", "local"),
        ("2", "Step 2 — Signed build", "release"),
    ]
    assert orphans == []


def test_numbered_items_are_steps_unless_step_headings_exist() -> None:
    numbered = plan_text("1. Cache layer.\n2. Signed build.\n   **Evidence class:** release\n")
    assert [s.evidence_class for s in plan_steps(numbered)[0]] == ["local", "release"]
    headed = plan_text("### Step 1 — Build\n\n1. compile\n2. sign\n\n**Evidence class:** release\n")
    assert [(s.label, s.evidence_class) for s in plan_steps(headed)[0]] == [("1", "release")]


def test_step_label_comes_from_its_title_not_its_position() -> None:
    text = plan_text(
        "### Step 0 — Setup\n\n### Step 2.5 — Sign\n\n> **Evidence class:** release\n\n"
        "### Step 5 — Ship\n"
    )
    assert [(s.label, s.evidence_class) for s in plan_steps(text)[0]] == [
        ("0", "local"),
        ("2.5", "release"),
        ("5", "local"),
    ]
    inline = plan_text("1. Build `make_x`.\n2. Notarize. **Evidence class:** release\n")
    assert [(s.label, s.title, s.evidence_class) for s in plan_steps(inline)[0]] == [
        ("1", "Build make_x.", "local"),
        ("2", "Notarize.", "release"),
    ]


def test_quoted_or_hidden_evidence_lines_are_ignored() -> None:
    text = plan_text(
        "### Step 1 — Doc\n\n```markdown\n**Evidence class:** bogus\n```\n\n"
        "<!--\n**Evidence class:** bogus\n-->\nWrite `**Evidence class:** release` here.\n"
    )
    assert evidence_class_errors(text) == []


def test_step_labels_drop_leading_zeros() -> None:
    text = plan_text("### Step 02 — A\n\n**Evidence class:** release\n\n### Step 2 — B\n")
    assert [s.label for s in plan_steps(text)[0]] == ["2", "2"]
    assert any("Step 2 appears 2 times" in e for e in evidence_class_errors(text))


def test_long_whitespace_runs_stay_linear() -> None:
    lines = ["# a" + " " * 20000 + "x", "### Step 1" + " " * 20000 + "x"]
    lines.append("Evidence class" + " " * 20000 + "x")
    started = time.perf_counter()
    evidence_class_errors(plan_text("\n".join(lines)))
    assert time.perf_counter() - started < 1.0


# @spec AC-003: Unknown evidence class rejected
#   — .specs/features/090-minimal-plan-scope/spec.md#ac-003
@pytest.mark.parametrize(
    ("steps", "message"),
    [
        ("### Step 1 — Build\n\n**Evidence class:** device\n", "unknown evidence class 'device'"),
        (
            "### Step 1 — Build\n\n**Evidence class:** local\n**Evidence class:** release\n",
            "declares 2 evidence classes",
        ),
        ("**Evidence class:** release\n\n### Step 1 — Build\n", "outside an implementation"),
        ("### Step 1 — Build\n\n| a | **Evidence class:** release |\n", "not recognised"),
        ("### Step 1 — Build\n\n__Evidence class:__ release\n", "not recognised"),
        ("### Step 1 — Build\n\n**Evidence class: release**\n", "not recognised"),
        ("### Step 1 — Build\n\n*Evidence class:* release\n", "not recognised"),
        ("### Step 1 — Build\n\nEvidence class: release\n", "not recognised"),
        ("### Step 1 — Build\n\n**Evidence  class:** release\n", "not recognised"),
        ("### Step 1 — Sign **Evidence class:** release\n", "not recognised"),
        ("### Step 1 — Build\n\n#### **Evidence class:** release\n", "not recognised"),
        ("1. Sign __Evidence class:__ release\n", "not recognised"),
        (
            "### Step 1 — A\n\n**Evidence class:** release\n\n### Step 1 — B\n",
            "Step 1 appears 2 times",
        ),
    ],
)
def test_invalid_evidence_classes_are_reported(steps: str, message: str) -> None:
    errors = evidence_class_errors(plan_text(steps))
    assert any(message in error for error in errors), errors


def test_validate_plan_rejects_unknown_class(tmp_path: Path) -> None:
    feature = tmp_path / ".specs/features" / FEATURE
    feature.mkdir(parents=True)
    (feature / "plan.md").write_text(RELEASE_PLAN.replace("release\n", "staging\n", 1))
    result = CliRunner().invoke(app, ["validate", str(feature / "plan.md"), "--format", "full"])
    assert result.exit_code == 1
    assert "unknown evidence class 'staging'" in result.output
    (feature / "plan.md").write_text(RELEASE_PLAN)
    assert CliRunner().invoke(app, ["validate", str(feature / "plan.md")]).exit_code == 0


def _plan_review(root: Path, scope: dict[str, Any] | None) -> bool:
    prepared = prepare_feature_review(root, FEATURE, "plan", MODEL)
    response = json.loads(grounded_response(prepared))
    plan = next(s for s in prepared.sections if s.role == "plan")
    if scope:
        citation = {"section_id": plan.section_id, "excerpt": plan.text}
        response["extra_scope"] = [{**scope, "citations": [citation]}]
    receipt, _ = ingest_feature_review(root, FEATURE, "plan", [json.dumps(response)])
    assert receipt.complete, receipt.errors
    return receipt.ready


# @spec AC-001: Untraced mechanism flagged and blocking (SC-002)
#   — .specs/features/090-minimal-plan-scope/spec.md#ac-001
def test_plan_review_prompt_carries_minimal_scope_rule(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    plan = prepare_feature_review(root, FEATURE, "plan", MODEL)
    spec = prepare_feature_review(root, FEATURE, "spec", MODEL)
    assert all("Minimal spec scope" in batch.prompt for batch in plan.batches)
    assert not any("Minimal spec scope" in batch.prompt for batch in spec.batches)


def test_untraced_cache_blocks_unless_justified_technical_necessity(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    write_plan(root, "# Plan\nFR-001 AC-001 Delete old exports hourly behind a result cache.\n")
    cache = {"description": "Result cache", "justification": "", "approved": False}
    assert not _plan_review(root, {**cache, "kind": "business"})
    necessity = {
        "description": "Atomic rename of the export index",
        "justification": "FR-001 deletes while readers list exports",
        "approved": False,
        "kind": "technical",
    }
    assert _plan_review(root, necessity)
    assert not _plan_review(root, {**necessity, "justification": ""})


def test_native_rule_is_cited_by_the_review_protocol() -> None:
    rule = LIVESPEC_ROOT / "system/minimal-spec-scope.md"
    assert "extra_scope" in rule.read_text(encoding="utf-8")
    protocol = (LIVESPEC_ROOT / "system/review-protocol.md").read_text(encoding="utf-8")
    assert "(minimal-spec-scope.md)" in protocol


@pytest.mark.parametrize("destination", [*PROGRESSION_DESTINATIONS, "bogus"])
def test_cli_progression_choices_match_the_gate(destination: str) -> None:
    options = SemanticOptions(
        clarification=False,
        prepare=None,
        ingest=None,
        progression=destination,
        pre_impl=False,
        structural_only=False,
        state_files=False,
        kind="plan",
        budget=None,
    )
    if destination in PROGRESSION_DESTINATIONS:
        check_semantic_options(options, {})
    else:
        with pytest.raises(ValueError, match="unknown_progression_destination"):
            check_semantic_options(options, {})
