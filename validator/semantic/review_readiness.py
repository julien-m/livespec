"""Review readiness from blockers only (feature 088); proof reviews stay strict."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from validator.semantic.review_contract import (
        Ambiguity,
        RequirementConclusion,
        ReviewReceipt,
        ScopeFinding,
    )


def scope_accepted(scope: ScopeFinding) -> bool:
    """Approved scope, or a technical necessity carrying a justification (088)."""
    return scope.approved or (scope.kind == "technical" and bool(scope.justification.strip()))


def conclusion_blocks(conclusion: RequirementConclusion, ambiguities: list[Ambiguity]) -> bool:
    """Only an unexplained or critically ambiguous conclusion blocks besides non-coverage."""
    # @spec FR-001: Non-critical ambiguity carries over
    #   — .specs/features/088-capped-reviews/spec.md#fr-001
    if conclusion.disposition == "covered":
        return False
    if conclusion.disposition != "ambiguous":
        return True
    own = [item for item in ambiguities if item.requirement_id == conclusion.requirement_id]
    return not own or any(item.critical and not item.resolution for item in own)


def strictly_ready(receipt: ReviewReceipt) -> bool:
    """Proof-bearing reviews (acceptance, mapping) keep the pre-088 rule: all covered."""
    return (
        receipt.ready
        and all(c.disposition == "covered" for c in receipt.conclusions)
        and all(scope.approved for scope in receipt.extra_scope)
    )


def carry_over(receipt: ReviewReceipt) -> list[str]:
    """Non-blocking items the next phase must address: warnings, open ambiguities, scope."""
    items = [
        f"{finding.severity}: {finding.category}: {finding.description}"
        for finding in receipt.findings
        if finding.severity != "blocking"
    ]
    items.extend(
        f"ambiguity: {item.requirement_id}: {item.question}"
        for item in receipt.ambiguities
        if not item.critical and not item.resolution
    )
    items.extend(
        f"technical scope: {scope.description}: {scope.justification}"
        for scope in receipt.extra_scope
        if not scope.approved and scope_accepted(scope)
    )
    return items
