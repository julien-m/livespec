"""Paired long-plan review and cross-batch issue survival counterexamples."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from tests.test_review_context import response
from validator.semantic.review_context import prepare_review_context
from validator.semantic.review_contract import ReviewResponse, validate_review_result
from validator.semantic.review_receipts import run_prepared_review
from validator.semantic.review_synthesis import issue_ledger


def long_context(contradictory: bool = False):
    chapters = [
        f"## Step {i}\n" + "Detail " * 360 + "\nRemove exports after 24h.\n" for i in range(3)
    ]
    if contradictory:
        chapters[-1] = chapters[-1].replace("Remove exports after 24h.", "Keep exports forever.")
    return prepare_review_context(
        "f",
        {"spec": "FR-001 Delete exports after 24h.", "plan": "".join(chapters)},
        model="reviewer",
        max_chars=5000,
    )


def judgments(context, contradictory=False):
    raws = []
    for index, _batch in enumerate(context.batches):
        raw = response(context, index=index)
        for conclusion in raw["conclusions"]:
            for citation in conclusion["plan_citations"]:
                text = citation["excerpt"]
                citation["excerpt"] = text.strip().splitlines()[-1]
                if contradictory and "Keep exports forever." in text:
                    conclusion["disposition"] = "contradictory"
        raws.append(raw)
    return raws


def synthesis(context, raws):
    final = dict(raws[0])
    final.update(
        batch_id="synthesis",
        synthesized_batch_ids=[b.batch_id for b in context.batches],
        reviewed_section_ids=[s.section_id for s in context.sections],
    )
    if any(c["disposition"] == "contradictory" for raw in raws for c in raw["conclusions"]):
        final["conclusions"] = [
            next(
                c for raw in raws for c in raw["conclusions"] if c["disposition"] == "contradictory"
            )
        ]
    return final


@pytest.mark.parametrize("contradictory", [False, True])
def test_real_plan_batches_compare_all_plan_bytes_with_contract(contradictory):
    context = long_context(contradictory)
    assert context.complete and len(context.batches) == 3
    sections = {s.section_id: s for s in context.sections}
    seen_plan = set()
    for batch in context.batches:
        assert batch.requirement_ids == ("f:FR-001",)
        assert any(sections[s].role == "spec" for s in batch.section_ids)
        plan_ids = {s for s in batch.section_ids if sections[s].role == "plan"}
        assert plan_ids
        seen_plan.update(plan_ids)
        assert len(batch.prompt) <= context.max_chars
    assert seen_plan == {s.section_id for s in context.sections if s.role == "plan"}
    raws = judgments(context, contradictory)
    outputs = [*raws, synthesis(context, raws)]
    with patch(
        "validator.llm_provider.call_llm", side_effect=[json.dumps(o) for o in outputs]
    ) as provider:
        receipt = run_prepared_review(context)
    assert receipt.complete, receipt.errors
    assert receipt.ready is not contradictory
    assert provider.call_count == 4
    assert all(len(call.args[0]) <= context.max_chars for call in provider.call_args_list)


@pytest.mark.parametrize("kind", ["ambiguity", "finding", "scope", "contradiction"])
def test_synthesis_cannot_erase_blockers_without_grounded_resolution(kind):
    context = long_context()
    raws = judgments(context)
    citation = raws[0]["conclusions"][0]["source_citations"]
    if kind == "ambiguity":
        raws[0]["ambiguities"] = [
            dict(
                requirement_id="f:FR-001",
                decision_key="retention",
                question="Purge exports or source records?",
                critical=True,
                citations=citation,
            )
        ]
    elif kind == "finding":
        raws[0]["findings"] = [
            dict(
                category="permissions",
                severity="blocking",
                description="Missing authorization",
                suggestion="Check permissions",
                citations=citation,
            )
        ]
    elif kind == "scope":
        raws[0]["extra_scope"] = [
            dict(
                description="Email exported content",
                approved=False,
                justification="",
                citations=citation,
            )
        ]
    else:
        raws[0]["conclusions"][0]["disposition"] = "contradictory"
    final = synthesis(context, judgments(context))
    encoded = [json.dumps(r) for r in raws]
    erased = validate_review_result(context, encoded, json.dumps(final))
    assert not erased.complete and not erased.ready
    assert "unresolved_batch_issues_erased" in erased.errors
    key = next(iter(issue_ledger(ReviewResponse.model_validate(raws[0]))))
    final["resolutions"] = [
        dict(issue_key=key, rationale="Reconciled against approved rule.", citations=citation)
    ]
    assert validate_review_result(context, encoded, json.dumps(final)).ready
    final["resolutions"][0]["citations"][0]["excerpt"] = "Invented permission"
    assert not validate_review_result(context, encoded, json.dumps(final)).ready


def test_synthesis_cannot_claim_covered_from_missing_only_batch_summaries():
    context = long_context()
    raws = judgments(context)
    final = synthesis(context, judgments(context))
    for raw in raws:
        for conclusion in raw["conclusions"]:
            conclusion["disposition"] = "missing"
            conclusion["searched_plan_sections"] = [
                c["section_id"] for c in conclusion["plan_citations"]
            ]
            conclusion["plan_citations"] = []
    receipt = validate_review_result(context, [json.dumps(r) for r in raws], json.dumps(final))
    assert not receipt.ready
    assert "synthesis_citation_not_observed_in_batch" in receipt.errors
