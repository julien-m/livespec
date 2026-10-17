"""Balanced fallback keeps paired evidence while avoiding avoidable review calls."""

from __future__ import annotations

from validator.semantic.review_batches import build_batches
from validator.semantic.review_context import PreparedReview, prepare_review_context
from validator.semantic.review_stability import _authentic, reviewed_snapshot


def _context() -> PreparedReview:
    return prepare_review_context(
        "release",
        {
            "spec": "# Contract\n## AC-001\nThe release remains locally operable.\n",
            "plan": "# Plan\n"
            + "".join(
                f"## Step {i}\n"
                + "Validate local operation and reject ambiguous release targets. " * 8
                + "\n"
                for i in range(8)
            ),
            "contracts": "# Approved contracts\n"
            + "".join(
                f"## Contract {i}\n"
                + "Retain explicit namespace isolation and operator diagnostics. " * 12
                + "\n"
                for i in range(16)
            ),
            "constitution": "# Constitution\nLocal effects only.\n",
        },
        source_roles={
            "spec": "spec",
            "plan": "plan",
            "constitution": "constitution",
            "contracts": "reference",
        },
        source_features={name: "release" for name in ("spec", "plan", "contracts", "constitution")},
        model="reviewer/v1",
        max_chars=6000,
    )


def _legacy(context: PreparedReview) -> PreparedReview:
    batches, errors = build_batches(
        context.kind,
        list(context.sections),
        context.requirements,
        context.max_chars,
        legacy_plan_packing=True,
    )
    assert not errors
    return context.model_copy(update={"batches": batches})


# @spec FR-002: Fallback uses bounded groups without losing paired normative evidence
# — .specs/features/078-requirement-evidence-integrity/spec.md#fr-002
def test_balanced_fallback_reduces_calls_with_complete_exact_coverage() -> None:
    context = _context()
    baseline = _legacy(context)
    assert context.complete, context.errors
    assert len(context.batches) < len(baseline.batches)
    assert context == _context()
    groups = [set(batch.section_ids) for batch in context.batches]
    assert set().union(*groups) == {s.section_id for s in context.sections}
    plans = [s for s in context.sections if s.role == "plan"]
    sources = [s for s in context.sections if s.role in ("spec", "reference")]
    assert all(
        any(s.section_id in g and p.section_id in g for g in groups) for s in sources for p in plans
    )
    assert all(len(b.prompt) <= context.max_chars for b in context.batches)
    assert {r for b in context.batches for r in b.requirement_ids} == {"release:AC-001"}


def test_explicit_legacy_layout_and_authenticity_stay_exact() -> None:
    baseline = _legacy(_context())
    assert len(baseline.batches) == 45
    assert _legacy(baseline).batches == baseline.batches
    assert _authentic(reviewed_snapshot(baseline), baseline.context_hash)


def test_no_gain_and_indivisible_over_budget_keep_existing_behavior() -> None:
    context = prepare_review_context(
        "release",
        {
            "spec": "## AC-001\n" + "Retain local records. " * 20,
            "plan": "## Step 1\n"
            + "Validate records. " * 40
            + "\n## Step 2\n"
            + "Reject release. " * 40,
        },
        max_chars=3000,
    )
    assert context.complete, context.errors
    assert context.batches == _legacy(context).batches
    blocked = prepare_review_context(
        "release",
        {"spec": "AC-001: " + "Retain records. " * 400, "plan": "Validate records. " * 400},
        max_chars=3000,
    )
    assert not blocked.complete and not blocked.batches
    assert "indivisible_paired_context_over_budget" in blocked.errors
