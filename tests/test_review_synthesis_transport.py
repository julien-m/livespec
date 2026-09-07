"""Lossless synthesis transport cannot bypass producer or consumer budgets."""

import hashlib
import json
from unittest.mock import patch

from tests.test_review_batching import judgments, long_context, synthesis
from validator.semantic.review_contract import ReviewResponse, validate_review_result
from validator.semantic.review_receipts import (
    load_review_receipt,
    run_prepared_review,
    synthesis_prompt,
    verify_review_receipt,
)
from validator.semantic.review_synthesis import issue_ledger
from validator.semantic.review_synthesis_transport import (
    expand_synthesis_raws,
    expand_synthesis_sections,
    pack_synthesis_raws,
    synthesis_payload,
)


def test_shared_lists_reconstruct_every_original_raw_character():
    ids = [f"long-source-é/{index:03}/section-with-a-long-stable-identity" for index in range(40)]
    row = {"reviewed_section_ids": ids, "searched_plan_sections": ids, "rationale": "Unchanged."}
    raws = [json.dumps(row, ensure_ascii=False, indent=2), json.dumps(row, ensure_ascii=False)]
    packed = pack_synthesis_raws(raws)
    assert len(packed["shared_lists"]) == 2  # Different whitespace remains exactly preserved.
    assert expand_synthesis_raws(packed) == raws
    assert len(json.dumps(packed)) < len(json.dumps(raws))
    assert [json.loads(raw) for raw in expand_synthesis_raws(packed)] == [row, row]


def test_transport_preserves_all_judgments_citations_and_issue_ledgers():
    context = long_context(contradictory=True)
    responses = judgments(context, contradictory=True)
    raws = [json.dumps(row, indent=2) for row in responses]
    payload = synthesis_payload(context, raws)
    assert expand_synthesis_raws(payload) == raws
    assert payload["issue_ledgers"] == [
        issue_ledger(ReviewResponse.model_validate(row)) for row in responses
    ]
    assert payload["requirements"] == [row.model_dump() for row in context.requirements]
    assert expand_synthesis_sections(payload) == [row.section_id for row in context.sections]
    final = synthesis(context, responses)
    receipt = validate_review_result(context, raws, json.dumps(final))
    assert receipt.complete and not receipt.ready
    assert receipt.conclusions[0].disposition == "contradictory"


def test_synthesis_budget_blocks_provider_dispatch_and_native_ingestion():
    context = long_context()
    responses = judgments(context)
    for row in responses:
        row["conclusions"][0]["rationale"] = "Full reviewer judgment. " * 1000
    raws = [json.dumps(row) for row in responses]
    final = json.dumps(synthesis(context, responses))
    assert len(synthesis_prompt(context, raws)) > context.max_chars
    with patch("validator.llm_provider.call_llm", side_effect=raws) as provider:
        automatic = run_prepared_review(context)
    native = validate_review_result(context, raws, final)
    assert provider.call_count == len(context.batches)
    assert not automatic.complete and not native.complete
    assert "synthesis_context_over_budget" in automatic.errors
    assert "synthesis_context_over_budget" in native.errors
    assert automatic.raw_results == native.raw_results == raws


def test_old_multi_receipt_is_readable_but_requires_fresh_synthesis(tmp_path):
    context = long_context()
    responses = judgments(context)
    raws = [json.dumps(row) for row in responses]
    final = json.dumps(synthesis(context, responses))
    receipt = validate_review_result(context, raws, final)
    assert receipt.ready and receipt.synthesis_transport_version == "3"
    historical = receipt.model_dump()
    historical.pop("synthesis_transport_version")
    path = tmp_path / "old-review.json"
    path.write_text(json.dumps(historical))
    loaded = load_review_receipt(path)
    assert loaded.raw_results == raws and loaded.synthesis == final
    assert not verify_review_receipt(loaded, context)
    before = [hashlib.sha256(b.prompt.encode()).hexdigest() for b in context.batches]
    with patch("validator.llm_provider.call_llm", side_effect=[*raws, final]) as provider:
        current = run_prepared_review(context, cache_path=path)
    assert provider.call_count == len(context.batches) + 1
    assert current.ready and verify_review_receipt(current, context)
    assert [hashlib.sha256(b.prompt.encode()).hexdigest() for b in context.batches] == before


def test_historical_policy1_archive_loads_without_claiming_current_multi_evidence(tmp_path):
    from validator.run_artifacts import load_run_artifact

    context = long_context()
    responses = judgments(context)
    raws = [json.dumps(row) for row in responses]
    old = validate_review_result(
        context, raws, json.dumps(synthesis(context, responses))
    ).model_dump()
    old.pop("synthesis_transport_version")
    receipt_path = tmp_path / "historical-review.json"
    receipt_path.write_text(json.dumps(old))
    artifact = {
        "schema_version": "2.0",
        "evidence_policy_version": "1",
        "goal_hash": "a" * 64,
        "command": "spec-demo",
        "flags": [],
        "timestamp": "2026-01-01T00:00:00Z",
        "goal": {"tasks": []},
        "verify_rules": {},
        "verify_result": {},
        "receipts": [{"kind": "review", "path": str(receipt_path)}],
    }
    path = tmp_path / "spec-demo-2026-01-01T00-00-00-aaaaaaaa.json"
    path.write_text(json.dumps(artifact))
    assert load_run_artifact(path) == artifact
    assert load_review_receipt(receipt_path).raw_results == raws
    assert not verify_review_receipt(receipt_path, context)


def test_unchanged_single_batch_receipt_keeps_legacy_cache_readability(tmp_path):
    from tests.test_review_context import response
    from validator.semantic.review_context import prepare_review_context

    context = prepare_review_context("f", {"spec": "FR-001 Keep exports."}, kind="spec", model="m")
    receipt = validate_review_result(context, [json.dumps(response(context))])
    assert receipt.ready and receipt.synthesis_transport_version is None
    old = receipt.model_dump()
    old.pop("synthesis_transport_version")
    path = tmp_path / "single.json"
    path.write_text(json.dumps(old))
    assert verify_review_receipt(path, context)
