"""Bound Plan review work without fragmenting a Plan that fits beside each source."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from tests.test_review_batching import synthesis
from tests.test_review_context import response
from validator.semantic.review_context import PreparedReview, prepare_review_context
from validator.semantic.review_contract import validate_review_result
from validator.semantic.review_stability import _authentic, prepare_like, reviewed_against


def _assert_coverage(context: PreparedReview) -> None:
    assert context.complete, context.errors
    assert {s.section_id for s in context.sections} == {
        section_id for batch in context.batches for section_id in batch.section_ids
    }
    assert {r.requirement_id for r in context.requirements} == {
        requirement_id for batch in context.batches for requirement_id in batch.requirement_ids
    }
    assert all(len(batch.prompt) <= context.max_chars for batch in context.batches)


# @spec FR-002: Coherent bounded batches retain complete normative context
#   — .specs/features/078-requirement-evidence-integrity/spec.md#fr-002
def test_complete_plan_reservation_prevents_cartesian_review_explosion() -> None:
    sources = {"spec": "# Contract\nFR-001: Persist the uploaded object.\n"}
    sources["plan"] = "".join(
        f"## Step {index}\n" + "Persist and verify the committed upload. " * 35 + "\n"
        for index in range(25)
    )
    sources.update(
        {f"contract-{i}": f"# Contract {i}\n" + "Contract detail. " * 2764 for i in range(12)}
    )
    roles = {name: "reference" for name in sources if name.startswith("contract-")}
    context = prepare_review_context(
        "uploads", sources, source_roles=roles, model="reviewer", max_chars=200000
    )
    _assert_coverage(context)
    plan_ids = {s.section_id for s in context.sections if s.role == "plan"}
    assert 1 < len(context.batches) <= 4
    assert all(plan_ids <= set(batch.section_ids) for batch in context.batches)
    source_counts = Counter(section_id for b in context.batches for section_id in b.section_ids)
    assert all(source_counts[s.section_id] == 1 for s in context.sections if s.role != "plan")
    assert sum(len(batch.requirement_ids) for batch in context.batches) == 1
    assert context == prepare_review_context(
        "uploads", sources, source_roles=roles, model="reviewer", max_chars=200000
    )


def test_plan_larger_than_budget_still_compares_every_source_plan_pair() -> None:
    context = prepare_review_context(
        "uploads",
        {
            "spec": "".join(
                f"## FR-{i:03d}\n" + "Persist uploads. " * 50 + "\n" for i in range(1, 4)
            ),
            "plan": "".join(f"## Step {i}\n" + "Commit uploads. " * 100 + "\n" for i in range(3)),
        },
        model="reviewer",
        max_chars=4500,
    )
    _assert_coverage(context)
    specs = [s.section_id for s in context.sections if s.role == "spec"]
    plans = [s.section_id for s in context.sections if s.role == "plan"]
    assert all(
        any(spec in b.section_ids and plan in b.section_ids for b in context.batches)
        for spec in specs
        for plan in plans
    )


def test_indivisible_pair_over_budget_stays_explicitly_incomplete() -> None:
    context = prepare_review_context(
        "uploads",
        {"spec": "FR-001 Persist uploads. " * 200, "plan": "Commit uploads. " * 200},
        model="reviewer",
        max_chars=4500,
    )
    assert not context.complete and not context.batches
    assert "indivisible_paired_context_over_budget" in context.errors


def test_authentic_historical_layout_stays_valid_but_modified_spans_are_rejected() -> None:
    fixture = Path(__file__).parent / "fixtures/review-plan-packing-legacy.json"
    reviewed = PreparedReview.model_validate_json(fixture.read_text())
    assert _authentic(reviewed, reviewed.context_hash)
    texts = dict.fromkeys(reviewed.source_hashes, "")
    for section in reviewed.sections:
        texts[section.source] += section.text
    current = prepare_like(reviewed, texts, reviewed.dependencies)
    raws = [response(reviewed, index=index) for index in range(len(reviewed.batches))]
    for raw in raws:
        for conclusion in raw["conclusions"]:
            for field in ("source_citations", "plan_citations"):
                for citation in conclusion[field]:
                    citation["excerpt"] = citation["excerpt"][:40]
    receipt = validate_review_result(
        reviewed, [json.dumps(raw) for raw in raws], json.dumps(synthesis(reviewed, raws))
    )
    assert receipt.ready, receipt.errors
    assert reviewed_against(receipt, current) is not None
    section = reviewed.sections[0].model_copy(update={"text": "Invented commitment"})
    forged = reviewed.model_copy(update={"sections": (section, *reviewed.sections[1:])})
    assert not _authentic(forged, reviewed.context_hash)
    batch = reviewed.batches[0].model_copy(update={"section_ids": ()})
    forged = reviewed.model_copy(update={"batches": (batch, *reviewed.batches[1:])})
    assert not _authentic(forged, reviewed.context_hash)
