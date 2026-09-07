"""Reject incomplete per-assertion grounding before a mapping reaches the runner."""

# @spec(FR-009)
# @spec(FR-010)

from __future__ import annotations

from .semantic.review_context import PreparedReview
from .semantic.review_contract import ReviewReceipt


def mapping_review_errors(prepared: PreparedReview, receipt: ReviewReceipt) -> list[str]:
    """Check each exact binding against the final independent review conclusions."""
    from .execution_mapping import AcceptanceMapping, _assertion_span, _source_texts

    sources = _source_texts(prepared)
    mappings: list[AcceptanceMapping] = []
    for text in sources.values():
        try:
            mappings.append(AcceptanceMapping.model_validate_json(text))
        except ValueError:
            continue
    if len(mappings) != 1:
        return ["prepared_acceptance_mapping_missing_or_ambiguous"]
    conclusions = {item.requirement_id: item for item in receipt.conclusions}
    sections = {item.section_id: item for item in prepared.sections}
    errors = []
    for binding in mappings[0].bindings:
        span = _assertion_span(binding, sources[binding.assertion_path])
        conclusion = conclusions.get(binding.requirement_id)
        if not (
            conclusion
            and conclusion.disposition == "covered"
            and any(
                citation.section_id in sections
                and sections[citation.section_id].source == binding.assertion_path
                and span in citation.excerpt
                for citation in conclusion.plan_citations
            )
        ):
            errors.append(
                f"ungrounded_acceptance_binding:{binding.requirement_id}:"
                f"{binding.test_id}:{binding.start_line}-{binding.end_line}"
            )
    return errors
