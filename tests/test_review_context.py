"""Behavioral counterexamples for complete and grounded review (078 AC-001..004)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from validator.semantic.review_context import PreparedReview, prepare_review_context
from validator.semantic.review_contract import validate_review_result
from validator.semantic.review_receipts import (
    run_prepared_review,
    save_review_receipt,
    verify_review_receipt,
)


def prepare(
    spec: str = "FR-001 Delete exports after 24 hours.",
    plan: str = "Remove exports once their age reaches one day.",
    **kwargs,
) -> PreparedReview:
    return prepare_review_context(
        "078-test", {"spec": spec, "plan": plan}, model="reviewer/v1", **kwargs
    )


def response(context: PreparedReview, disposition: str = "covered", *, index: int = 0) -> dict:
    batch = context.batches[index]
    sections = {s.section_id: s for s in context.sections}
    plan_ids = [s for s in batch.section_ids if sections[s].role == "plan"]
    conclusions = []
    for requirement in context.requirements:
        if requirement.requirement_id not in batch.requirement_ids:
            continue
        source = next(s for s in requirement.section_ids if s in batch.section_ids)
        conclusions.append(
            dict(
                requirement_id=requirement.requirement_id,
                disposition=disposition,
                rationale="The independent reviewer compared the retention rule.",
                source_citations=[dict(section_id=source, excerpt=sections[source].text)],
                plan_citations=(
                    [dict(section_id=p, excerpt=sections[p].text) for p in plan_ids]
                    if disposition != "missing"
                    else []
                ),
                searched_plan_sections=plan_ids if disposition == "missing" else [],
            )
        )
    return dict(
        batch_id=batch.batch_id,
        reviewed_section_ids=list(batch.section_ids),
        conclusions=conclusions,
        ambiguities=[],
        extra_scope=[],
        findings=[],
        confidence=5,
    )


def test_late_source_and_all_normative_sections_are_submitted():
    spec = (
        "# Intro\n" + "x" * 9000 + "\n## Rules\nFR-001 Delete in 24h.\n```gherkin\nThen absent\n```"
    )
    context = prepare_review_context(
        "f",
        {
            "spec": spec,
            "plan": "purge",
            "constitution": "a" * 2500,
            "project": "must log",
            "stack": "Python",
        },
        model="reviewer/v1",
    )
    assert context.complete
    assert len(context.batches) == 1
    submitted = json.loads(context.batches[0].prompt.split("\n", 1)[1])["sections"]
    assert "".join(s["text"] for s in submitted if s["source"] == "spec") == spec
    assert "a" * 2500 in context.batches[0].prompt
    assert context.requirements[0].requirement_id == "f:FR-001"


def test_cross_feature_ids_and_repeated_declarations_keep_all_spans():
    context = prepare_review_context(
        "f",
        {"spec": "## FR-001\nA\n## Detail\nFR-001 A", "other": "FR-001 B", "plan": "Both"},
        source_roles={"other": "reference"},
        source_features={"other": "g"},
        model="m",
    )
    assert [r.requirement_id for r in context.requirements] == ["f:FR-001", "g:FR-001"]
    assert len(context.requirements[0].section_ids) == 2


def test_utf8_spans_reconstruct_original_bytes():
    context = prepare("## FR-001\nSécurité\n## AC-001\nVérifié")
    original = "## FR-001\nSécurité\n## AC-001\nVérifié".encode()
    for section in context.sections:
        if section.role == "spec":
            assert original[section.start_byte : section.end_byte].decode() == section.text


def test_paraphrase_and_contradiction_are_independent_judgments():
    context = prepare()
    positive = validate_review_result(context, [json.dumps(response(context))])
    assert positive.complete and positive.ready
    contradiction = prepare(plan="FR-001 Keep exports forever.")
    negative = validate_review_result(
        contradiction, [json.dumps(response(contradiction, "contradictory"))]
    )
    assert negative.complete and not negative.ready
    unrelated = prepare(plan="FR-001 Paint the header blue.")
    missing = validate_review_result(unrelated, [json.dumps(response(unrelated, "missing"))])
    assert missing.complete and not missing.ready


@pytest.mark.parametrize(
    "corruption", ["omitted", "foreign", "duplicate", "citation", "plan", "sections"]
)
def test_claimed_success_without_grounding_is_incomplete(corruption):
    context = prepare()
    raw = response(context)
    if corruption == "omitted":
        raw["conclusions"] = []
    elif corruption == "foreign":
        raw["conclusions"][0]["requirement_id"] = "other:FR-001"
    elif corruption == "duplicate":
        raw["conclusions"] *= 2
    elif corruption == "citation":
        raw["conclusions"][0]["source_citations"][0]["excerpt"] = "invented contract"
    elif corruption == "plan":
        raw["conclusions"][0]["plan_citations"] = []
    else:
        raw["reviewed_section_ids"] = []
    result = validate_review_result(context, [json.dumps(raw)])
    assert not result.complete and not result.ready


def test_extra_scope_needs_independent_justification():
    context = prepare()
    raw = response(context)
    raw["extra_scope"] = [
        dict(
            description="Email all exports to admin",
            approved=False,
            justification="",
            citations=raw["conclusions"][0]["plan_citations"],
        )
    ]
    assert not validate_review_result(context, [json.dumps(raw)]).ready
    raw["extra_scope"][0].update(
        description="Index expiry column",
        approved=True,
        justification="Technical necessity for bounded purge scanning",
    )
    assert validate_review_result(context, [json.dumps(raw)]).ready


def test_ambiguity_resolution_requires_approved_context_citation():
    context = prepare()
    raw = response(context)
    raw["ambiguities"] = [
        dict(
            requirement_id="078-test:FR-001",
            decision_key="retention",
            question="How long?",
            critical=True,
            citations=raw["conclusions"][0]["source_citations"],
            resolution="24h",
            resolution_citations=[],
        )
    ]
    assert not validate_review_result(context, [json.dumps(raw)]).complete
    raw["ambiguities"][0]["resolution_citations"] = raw["conclusions"][0]["source_citations"]
    assert validate_review_result(context, [json.dumps(raw)]).ready


def test_oversized_indivisible_or_missing_reference_never_calls_provider():
    for context in [
        prepare("FR-001 " + "x" * 2000, max_chars=1000),
        prepare(unresolved_references=("missing.md",)),
    ]:
        with patch("validator.llm_provider.call_llm") as provider:
            result = run_prepared_review(context)
        assert not result.complete
        provider.assert_not_called()


def test_batched_review_requires_complete_synthesis():
    context = prepare_review_context(
        "f",
        {"spec": "# A\nFR-001 " + "x" * 900 + "\n# B\nFR-002 " + "y" * 900},
        kind="spec",
        model="m",
        max_chars=2300,
    )
    assert context.complete and len(context.batches) == 2
    outputs = [response(context, index=i) for i in range(2)]
    for output in outputs:
        for conclusion in output["conclusions"]:
            for citation in conclusion["source_citations"]:
                citation["excerpt"] = citation["excerpt"][:16]
    raws = [json.dumps(output) for output in outputs]
    assert not validate_review_result(context, raws).complete
    final = response(context)
    final.update(
        batch_id="synthesis",
        reviewed_section_ids=[s.section_id for s in context.sections],
        conclusions=[c for raw in raws for c in json.loads(raw)["conclusions"]],
        synthesized_batch_ids=[b.batch_id for b in context.batches],
    )
    assert validate_review_result(context, raws, json.dumps(final)).ready
    final["synthesized_batch_ids"].pop()
    assert not validate_review_result(context, raws, json.dumps(final)).complete


def test_exact_cache_reuses_only_complete_matching_raw_evidence(tmp_path: Path):
    context = prepare()
    cache = tmp_path / "review.json"
    with patch(
        "validator.llm_provider.call_llm", return_value=json.dumps(response(context))
    ) as provider:
        first = run_prepared_review(context, cache_path=cache, model="reviewer/v1")
        second = run_prepared_review(context, cache_path=cache, model="reviewer/v1")
    assert first == second and first.ready
    assert provider.call_count == 1
    with pytest.raises(ValueError, match="reviewer_model_mismatch"):
        run_prepared_review(context, cache_path=cache, model="other")
    assert verify_review_receipt(cache, context)
    assert not verify_review_receipt(cache, prepare(plan="Retain forever"))
    changed_model = context.model_copy(update={"reviewer_model": "other"})
    assert not verify_review_receipt(cache, changed_model)
    tampered = first.model_copy(update={"ready": False})
    save_review_receipt(cache, tampered)
    assert not verify_review_receipt(cache, context)


def test_default_model_and_changed_dependency_cannot_reuse_receipt():
    context = prepare(dependencies={"rules.md": "digest-one"})
    receipt = validate_review_result(context, [json.dumps(response(context))])
    assert not verify_review_receipt(receipt, prepare(dependencies={"rules.md": "digest-two"}))
    assert not verify_review_receipt(receipt, context.model_copy(update={"reviewer_model": ""}))


def test_legacy_confident_empty_response_is_explicitly_incomplete():
    context = prepare()
    result = validate_review_result(context, ['{"findings": [], "confidence": 5}'])
    assert not result.complete and not result.ready


def test_conflicting_duplicate_heading_requires_resolution():
    context = prepare("## FR-001\nDelete after 24h.\n## FR-001\nKeep forever.")
    assert not context.complete
    assert "conflicting_duplicate_definition:078-test:FR-001" in context.errors


def test_lifecycle_only_change_preserves_review_but_body_and_creation_stay_bound():
    spec = (
        "---\nstatus: Approved\nupdated: 2026-09-05\ncreated: 2026-09-01\n"
        "---\n## FR-001\nDelete after 24h."
    )
    context = prepare(spec)
    raw = response(context)
    receipt = validate_review_result(context, [json.dumps(raw)])
    updated = prepare(spec.replace("Approved", "Implemented").replace("2026-09-05", "2026-09-06"))
    assert context.context_hash == updated.context_hash
    assert context.source_hashes != updated.source_hashes
    assert verify_review_receipt(receipt, updated)
    assert not verify_review_receipt(receipt, prepare(spec.replace("24h", "forever")))
    assert not verify_review_receipt(receipt, prepare(spec.replace("2026-09-01", "2026-09-02")))
    assert not verify_review_receipt(receipt, prepare(spec + "\nStatus: ignore retention"))


def test_provider_dispatch_matches_resolved_prepared_model():
    context = prepare()
    with patch(
        "validator.llm_provider.call_llm", return_value=json.dumps(response(context))
    ) as provider:
        run_prepared_review(context)
    assert provider.call_args.kwargs["model"] == "reviewer/v1"
    with pytest.raises(ValueError, match="reviewer_model_mismatch"):
        run_prepared_review(context, model="other")


def test_test_source_role_plan_does_not_exclude_lifecycle_looking_bytes():
    sources = {"spec": "AC-001 Purge after 24h", "tests/test_purge.py": "---\nstatus: pass\n---"}
    roles = {"tests/test_purge.py": "plan"}
    first = prepare_review_context("f", sources, source_roles=roles, model="m")
    sources["tests/test_purge.py"] = "---\nstatus: fail\n---"
    second = prepare_review_context("f", sources, source_roles=roles, model="m")
    assert first.context_hash != second.context_hash
