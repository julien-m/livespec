"""The receipt keeps the strictest QE assessment of a multi-batch review (feature 086 FR-009)."""

from __future__ import annotations

from typing import Literal

from validator.semantic.review_contract import QeAssessment, ReviewResponse
from validator.semantic.review_synthesis import strictest_assessment

Level = Literal["Low", "Medium", "High"]


def _response(criticality: Level | None, why: str = "x") -> ReviewResponse:
    assessment = None
    if criticality:
        citation = {"section_id": "spec:L1-L2", "excerpt": "QE"}
        assessment = QeAssessment.model_validate(
            {"criticality": criticality, "justification": why, "citations": [citation]}
        )
    return ReviewResponse.model_construct(qe_assessment=assessment)


# @spec AC-009: Contestable criticality and reviewed QE
#   — .specs/features/086-risk-proportional-delivery/spec.md#ac-009
def test_a_batch_high_survives_a_synthesis_without_assessment() -> None:
    batches = [_response("Low"), _response("High")]
    result = strictest_assessment(_response(None), batches)
    assert result is not None and result.criticality == "High"


def test_a_batch_high_beats_a_lower_synthesis_and_the_final_wins_ties() -> None:
    raised = strictest_assessment(_response("Low"), [_response("High")])
    assert raised is not None and raised.criticality == "High"
    tie = strictest_assessment(_response("Medium", "final"), [_response("Medium", "batch")])
    assert tie is not None and tie.justification == "final"
    assert strictest_assessment(_response(None), [_response(None)]) is None
