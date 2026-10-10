"""Current semantic receipts control Analyze and the complete Clarify inventory."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from validator.clarify_gate import scan_clarification_opportunities
from validator.clarify_inventory import (
    collect_clarification_inventory,
    persist_clarification_decision,
)
from validator.pre_impl_analysis import analyze_feature_artifacts, has_blocking_findings
from validator.semantic.review_context import PreparedReview, prepare_review_context
from validator.semantic.review_contract import validate_review_result
from validator.semantic.review_receipts import save_review_receipt


def _context(tmp_path: Path, spec: str, *, kind: str = "plan") -> tuple[Path, PreparedReview]:
    feature = tmp_path / "001-purge"
    feature.mkdir(exist_ok=True)
    (feature / "spec.md").write_text(spec)
    (feature / "plan.md").write_text("FR-001: Keep files forever.")
    sources = {"spec": spec, "constitution": "Only administrators may delete files."}
    (tmp_path / "constitution.md").write_text(sources["constitution"])
    if kind == "plan":
        sources["plan"] = (feature / "plan.md").read_text()
    prepared = prepare_review_context(
        feature.name, sources, kind="spec" if kind == "spec" else "plan", model="reviewer-v1"
    )
    return feature, prepared


def _raw(
    prepared: PreparedReview,
    *,
    disposition: str = "covered",
    ambiguities: list[dict[str, object]] | None = None,
) -> str:
    spec = next(s for s in prepared.sections if s.role == "spec")
    plan = next((s for s in prepared.sections if s.role == "plan"), None)
    conclusions = [
        {
            "requirement_id": r.requirement_id,
            "disposition": disposition,
            "rationale": "Independent judgment of the supplied behavior.",
            "source_citations": [{"section_id": spec.section_id, "excerpt": spec.text}],
            "plan_citations": [{"section_id": plan.section_id, "excerpt": plan.text}]
            if plan
            else [],
        }
        for r in prepared.requirements
    ]
    return json.dumps(
        {
            "batch_id": prepared.batches[0].batch_id,
            "reviewed_section_ids": [s.section_id for s in prepared.sections],
            "conclusions": conclusions,
            "ambiguities": ambiguities or [],
            "extra_scope": [],
            "findings": [],
            "confidence": 5,
        }
    )


def _save(feature: Path, prepared: PreparedReview, raw: str) -> Path:
    receipt = validate_review_result(prepared, [raw])
    assert receipt.complete, receipt.errors
    return save_review_receipt(feature / ".reviews" / f"{prepared.kind}.json", receipt)


# @spec FR-003: Semantic dispositions, not ID compliance
# — .specs/features/078-requirement-evidence-integrity/spec.md#fr-003


def test_matching_ids_cannot_override_contradictory_review(tmp_path: Path) -> None:
    feature, prepared = _context(tmp_path, "FR-001: Delete files after 24 hours.")
    path = _save(feature, prepared, _raw(prepared, disposition="contradictory"))
    report = analyze_feature_artifacts(
        feature, tmp_path / "constitution.md", review_receipt=path, prepared_review=prepared
    )
    assert report.coverage_percent == 100
    assert report.semantic_status == "blocked"
    assert has_blocking_findings(report)


def test_complete_equivalent_review_allows_semantic_readiness(tmp_path: Path) -> None:
    feature, _ = _context(tmp_path, "FR-001: Delete files after 24 hours.")
    (feature / "plan.md").write_text("FR-001: Remove every file at least one day old.")
    prepared = prepare_review_context(
        feature.name,
        {"spec": (feature / "spec.md").read_text(), "plan": (feature / "plan.md").read_text()},
        model="reviewer-v1",
    )
    path = _save(feature, prepared, _raw(prepared))
    report = analyze_feature_artifacts(
        feature, tmp_path / "constitution.md", review_receipt=path, prepared_review=prepared
    )
    assert report.semantic_status == "covered"
    assert not has_blocking_findings(report)


def test_missing_review_is_incomplete_even_with_all_ids(tmp_path: Path) -> None:
    feature, _ = _context(tmp_path, "FR-001: Delete files after 24 hours.")
    report = analyze_feature_artifacts(feature, tmp_path / "constitution.md")
    assert report.coverage_percent == 100
    assert report.semantic_status == "incomplete"
    assert has_blocking_findings(report)


def test_changed_model_rejects_previous_semantic_review(tmp_path: Path) -> None:
    feature, prepared = _context(tmp_path, "FR-001: Delete files after 24 hours.")
    path = _save(feature, prepared, _raw(prepared))
    changed = prepare_review_context(
        feature.name,
        {"spec": (feature / "spec.md").read_text(), "plan": (feature / "plan.md").read_text()},
        model="reviewer-v2",
    )
    report = analyze_feature_artifacts(
        feature, tmp_path / "constitution.md", review_receipt=path, prepared_review=changed
    )
    assert report.semantic_status == "incomplete"


def _ambiguity(prepared: PreparedReview, *, resolved: bool = False) -> dict[str, object]:
    spec = next(s for s in prepared.sections if s.role == "spec")
    constitution = next(s for s in prepared.sections if s.role == "constitution")
    return {
        "requirement_id": prepared.requirements[0].requirement_id,
        "decision_key": "permission",
        "question": "Who may delete files?",
        "critical": True,
        "citations": [{"section_id": spec.section_id, "excerpt": spec.text}],
        "resolution": "Only administrators" if resolved else "",
        "resolution_citations": [
            {"section_id": constitution.section_id, "excerpt": constitution.text}
        ]
        if resolved
        else [],
    }


def test_approved_context_resolves_business_question(tmp_path: Path) -> None:
    feature, prepared = _context(tmp_path, "FR-001: Delete files.", kind="spec")
    path = _save(
        feature, prepared, _raw(prepared, ambiguities=[_ambiguity(prepared, resolved=True)])
    )
    inventory = collect_clarification_inventory(
        feature / "spec.md", review_receipt=path, prepared_review=prepared
    )
    assert not inventory.blocking
    assert not inventory.presented
    assert inventory.inventory[0].resolution_provenance


def test_duplicate_review_decisions_are_presented_once(tmp_path: Path) -> None:
    feature, prepared = _context(tmp_path, "FR-001: Delete files.", kind="spec")
    question = _ambiguity(prepared)
    path = _save(feature, prepared, _raw(prepared, ambiguities=[question, question]))
    inventory = collect_clarification_inventory(
        feature / "spec.md", review_receipt=path, prepared_review=prepared
    )
    assert inventory.blocking
    assert len(inventory.inventory) == len(inventory.presented) == 1


def test_six_critical_review_questions_are_never_lost(tmp_path: Path) -> None:
    feature, prepared = _context(tmp_path, "FR-001: Delete files.", kind="spec")
    questions = [dict(_ambiguity(prepared), decision_key=f"decision-{index}") for index in range(6)]
    path = _save(feature, prepared, _raw(prepared, ambiguities=questions))
    inventory = collect_clarification_inventory(
        feature / "spec.md", review_receipt=path, prepared_review=prepared
    )
    assert inventory.blocking
    assert len(inventory.inventory) == 6
    assert len(inventory.presented) == 5


def test_reversible_noncritical_choice_does_not_block(tmp_path: Path) -> None:
    feature, prepared = _context(tmp_path, "FR-001: Delete files.", kind="spec")
    question = dict(_ambiguity(prepared), critical=False, decision_key="private-helper-name")
    path = _save(feature, prepared, _raw(prepared, ambiguities=[question]))
    inventory = collect_clarification_inventory(
        feature / "spec.md", review_receipt=path, prepared_review=prepared
    )
    assert not inventory.blocking


def test_accepted_decision_preserves_ids_and_invalidates_prior_review(tmp_path: Path) -> None:
    feature, prepared = _context(
        tmp_path, "FR-001: [NEEDS CLARIFICATION] retention period", kind="spec"
    )
    path = _save(feature, prepared, _raw(prepared))
    spec = feature / "spec.md"
    opportunity = scan_clarification_opportunities(spec)[0]
    previous = spec.read_text()
    new_hash = persist_clarification_decision(spec, opportunity, "Retain for 24 hours.")
    assert new_hash != opportunity.source_hash
    assert previous in spec.read_text()
    assert "## Clarifications" in spec.read_text()
    inventory = collect_clarification_inventory(spec, review_receipt=path, prepared_review=prepared)
    assert inventory.blocking and not inventory.review_complete
    assert not inventory.presented
    assert inventory.inventory[0].resolution == "Retain for 24 hours."
    with pytest.raises(ValueError, match="stale"):
        persist_clarification_decision(spec, opportunity, "Keep forever.")


def test_mutated_plan_rejects_prepared_object_snapshot(tmp_path: Path) -> None:
    feature, prepared = _context(tmp_path, "FR-001: Delete files after 24 hours.")
    path = _save(feature, prepared, _raw(prepared))
    (feature / "plan.md").write_text("FR-001: New unreviewed behavior.")
    report = analyze_feature_artifacts(
        feature, tmp_path / "constitution.md", review_receipt=path, prepared_review=prepared
    )
    assert report.semantic_status == "incomplete"


def test_changed_approved_context_cannot_reuse_old_resolution(tmp_path: Path) -> None:
    feature, prepared = _context(tmp_path, "FR-001: Delete files.", kind="spec")
    path = _save(
        feature, prepared, _raw(prepared, ambiguities=[_ambiguity(prepared, resolved=True)])
    )
    (tmp_path / "constitution.md").write_text("Everyone may delete files.")
    inventory = collect_clarification_inventory(
        feature / "spec.md", review_receipt=path, prepared_review=prepared
    )
    assert inventory.blocking and not inventory.review_complete


@pytest.mark.parametrize("gap", ["ambiguous", "unapproved_scope"])
def test_complete_unready_spec_review_never_authorizes_plan(tmp_path: Path, gap: str) -> None:
    feature, prepared = _context(tmp_path, "FR-001: Delete files.", kind="spec")
    response = json.loads(
        _raw(prepared, disposition="ambiguous" if gap == "ambiguous" else "covered")
    )
    if gap == "unapproved_scope":
        source = next(s for s in prepared.sections if s.role == "spec")
        response["extra_scope"] = [
            {
                "description": "Also email the deleted contents.",
                "justification": "",
                "approved": False,
                "citations": [{"section_id": source.section_id, "excerpt": source.text}],
            }
        ]
    path = _save(feature, prepared, json.dumps(response))
    inventory = collect_clarification_inventory(
        feature / "spec.md", review_receipt=path, prepared_review=prepared
    )
    assert inventory.review_complete
    assert inventory.blocking
    assert "blocking_spec_review_findings" in inventory.errors
