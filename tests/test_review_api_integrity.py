"""Review purpose and resolved identity survive public wrapper boundaries (078 FR-009)."""

import json
from pathlib import Path
from typing import Literal
from unittest.mock import patch

import pytest

from validator.semantic.plan_review import review_plan
from validator.semantic.review_api import ingest_feature_review, verify_feature_review
from validator.semantic.review_context import PreparedReview, prepare_review_context
from validator.semantic.review_files import prepare_feature_review
from validator.semantic.spec_review import review_spec


def _raw(context: PreparedReview) -> str:
    batch = context.batches[0]
    sections = {section.section_id: section for section in context.sections}
    plans = [sections[key] for key in batch.section_ids if sections[key].role == "plan"]
    conclusions = [
        {
            "requirement_id": requirement.requirement_id,
            "disposition": "covered",
            "rationale": "The implementation preserves the specified retention period.",
            "source_citations": [
                {"section_id": key, "excerpt": sections[key].text}
                for key in requirement.section_ids
            ],
            "plan_citations": [
                {"section_id": section.section_id, "excerpt": section.text} for section in plans
            ],
        }
        for requirement in context.requirements
    ]
    return json.dumps(
        {
            "batch_id": batch.batch_id,
            "reviewed_section_ids": list(batch.section_ids),
            "conclusions": conclusions,
            "ambiguities": [],
            "extra_scope": [],
            "findings": [],
            "confidence": 5,
        }
    )


def _project(root: Path) -> str:
    feature = "001-retention"
    files = {
        f"features/{feature}/spec.md": "FR-001: Delete exports after 24 hours.",
        f"features/{feature}/plan.md": "Delete exports once their age reaches one day.",
        "constitution.md": "Keep the contract authoritative.",
        "stacks/_default.md": "Python",
        "project.md": "Export management",
    }
    for name, text in files.items():
        path = root / ".specs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return feature


@pytest.mark.parametrize("kind", ["spec", "plan"])
def test_receipt_cannot_satisfy_the_other_review_purpose(
    tmp_path: Path, kind: Literal["spec", "plan"]
) -> None:
    feature = _project(tmp_path)
    prepared = prepare_feature_review(tmp_path, feature, kind, "reviewer/v1")
    receipt, path = ingest_feature_review(
        tmp_path, feature, kind, [_raw(prepared)], model="reviewer/v1"
    )
    assert receipt.complete and receipt.ready
    assert verify_feature_review(tmp_path, feature, path, model="reviewer/v1")
    assert verify_feature_review(tmp_path, feature, path, model="reviewer/v1", expected_kind=kind)
    wrong: Literal["spec", "plan"] = "plan" if kind == "spec" else "spec"
    assert not verify_feature_review(
        tmp_path, feature, path, model="reviewer/v1", expected_kind=wrong
    )


@pytest.mark.parametrize("kind", ["spec", "plan"])
@pytest.mark.parametrize("resolved_model", ["reviewer/actual", ""])
def test_public_result_reports_receipt_model_without_inventing_default(
    kind: Literal["spec", "plan"], resolved_model: str
) -> None:
    sources = {"spec": "FR-001: Delete exports after 24 hours."}
    if kind == "plan":
        sources["plan"] = "Delete exports once their age reaches one day."
    prepared = prepare_review_context("001-retention", sources, kind=kind, model=resolved_model)
    with patch("validator.llm_provider.call_llm", return_value=_raw(prepared)) as transport:
        result = (
            review_spec(sources["spec"], prepared=prepared)
            if kind == "spec"
            else review_plan(sources["spec"], sources["plan"], prepared=prepared)
        )
    assert result.receipt is not None
    assert result.reviewer_model == result.receipt.reviewer_model == resolved_model
    assert transport.call_args.kwargs["model"] == (resolved_model or None)


@pytest.mark.parametrize("kind", ["spec", "plan"])
def test_wrapper_keeps_explicit_model_mismatch_as_an_error(kind: Literal["spec", "plan"]) -> None:
    prepared = prepare_review_context(
        "001-retention",
        {"spec": "FR-001: Delete exports.", "plan": "Delete exports."},
        kind=kind,
        model="reviewer/actual",
    )
    with (
        patch("validator.llm_provider.call_llm") as transport,
        pytest.raises(ValueError, match="reviewer_model_mismatch"),
    ):
        if kind == "spec":
            review_spec("FR-001: Delete exports.", model="reviewer/other", prepared=prepared)
        else:
            review_plan(
                "FR-001: Delete exports.",
                "Delete exports.",
                model="reviewer/other",
                prepared=prepared,
            )
    assert not transport.called
