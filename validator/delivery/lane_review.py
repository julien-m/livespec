"""What the spec review adds to the lane: its reviewed QE and its criticality (086 FR-009)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .lane import LaneDecision, LaneReason, classify

if TYPE_CHECKING:
    from ..semantic.review_context import PreparedReview
    from ..semantic.review_contract import ReviewReceipt


def _reviewed_spec(decision: LaneDecision, reviewed: PreparedReview) -> str | None:
    source = f".specs/features/{decision.feature}/spec.md"
    chunks = [s.text for s in reviewed.sections if s.role == "spec" and s.source.endswith(source)]
    return "".join(chunks) if chunks else None


# @spec FR-009: Reviewed QE and contestable criticality
#   — .specs/features/086-risk-proportional-delivery/spec.md#fr-009
def apply_review(decision: LaneDecision, receipt: ReviewReceipt, reviewed: PreparedReview) -> None:
    """Keep the stricter classification, then apply the reviewer's criticality assessment.

    A QE edit after the review never lowers the lane: every reason of the reviewed QE
    section is kept. The reviewer may raise the criticality to High, or lower an author's
    High to Low or Medium; it never changes the blast radius.
    """
    text = _reviewed_spec(decision, reviewed)
    if text is not None:
        seen = {(r.code, r.detail) for r in decision.reasons}
        for reason in classify(decision.feature, text).reasons:
            if (reason.code, reason.detail) not in seen:
                decision.reasons.append(reason)
    assessment = receipt.qe_assessment
    if assessment is None:
        return
    high = [r for r in decision.reasons if r.code == "criticality_high"]
    assessed = assessment.criticality.lower()
    if assessed == "high" and not high:
        detail = f"spec reviewer assessed High: {assessment.justification}"
        decision.reasons.append(LaneReason("criticality_high", detail))
    elif assessed in ("low", "medium") and high:
        decision.reasons = [r for r in decision.reasons if r.code != "criticality_high"]
        decision.contested = {
            "author": "high",
            "reviewer": assessed,
            "justification": assessment.justification,
        }
