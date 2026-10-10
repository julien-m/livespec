"""Lossless clarification inventory with source-bound decisions (078 FR-006 through FR-008)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path

from pydantic import ValidationError

from validator.clarify_decisions import (
    persist_clarification_decision as persist_clarification_decision,
)
from validator.clarify_gate import (
    ClarifyOpportunity,
    rank_clarification_opportunities,
    scan_clarification_opportunities,
)
from validator.review_source_identity import prepared_sources_current
from validator.semantic.review_context import PreparedReview
from validator.semantic.review_contract import ReviewReceipt


@dataclass(frozen=True)
class ClarificationInventory:
    """Presentation never removes pending business decisions from readiness."""

    inventory: tuple[ClarifyOpportunity, ...]
    presented: tuple[ClarifyOpportunity, ...]
    source_hash: str
    review_complete: bool
    errors: tuple[str, ...] = ()

    @property
    def blocking(self) -> bool:
        """Mandatory review and every critical decision must be resolved."""
        return (
            not self.review_complete
            or bool(self.errors)
            or any(item.critical and not item.resolution for item in self.inventory)
        )


def _review_items(
    receipt: ReviewReceipt,
    prepared: PreparedReview,
    spec_path: Path,
    source_hash: str,
) -> list[ClarifyOpportunity]:
    sections = {section.section_id: section for section in prepared.sections}
    result = []
    for item in receipt.ambiguities:
        citation = item.citations[0]
        section = sections[citation.section_id]
        result.append(
            ClarifyOpportunity(
                category="semantic business decision",
                question=item.question,
                impact=3 if item.critical else 1,
                uncertainty=3,
                evidence_path=spec_path if section.role == "spec" else Path(section.source),
                evidence_line=section.start_line,
                evidence_text=citation.excerpt,
                requirement_id=item.requirement_id,
                decision_key=item.decision_key,
                critical=item.critical,
                source_hash=source_hash,
                resolution=item.resolution,
                resolution_provenance=tuple(
                    f"{c.section_id}: {c.excerpt}" for c in item.resolution_citations
                ),
            )
        )
    return result


def _merge(
    deterministic: list[ClarifyOpportunity],
    semantic: list[ClarifyOpportunity],
) -> list[ClarifyOpportunity]:
    # The reviewer names the observable decision; identical marker excerpts can adopt that key.
    merged: dict[tuple[str, str], ClarifyOpportunity] = {}
    for item in [*deterministic, *semantic]:
        key = (item.requirement_id or str(item.evidence_line), item.decision_key)
        if item in semantic:
            aliases = [
                old_key
                for old_key, old in merged.items()
                if old.requirement_id == item.requirement_id
                and (
                    old.decision_key == item.decision_key
                    or (old.category == "placeholders" and old.evidence_text == item.evidence_text)
                )
            ]
            for old_key in aliases:
                if old_key != key:
                    del merged[old_key]
        previous = merged.get(key)
        if (
            previous
            and previous.resolution
            and item.resolution
            and previous.resolution != item.resolution
        ):
            item = replace(
                item,
                resolution="",
                resolution_provenance=(),
                critical=True,
                question=f"Conflicting approved resolutions: {item.question}",
            )
        merged[key] = item
    return rank_clarification_opportunities(list(merged.values()), limit=None)


# @spec FR-007: Lossless question inventory
# — .specs/features/078-requirement-evidence-integrity/spec.md#fr-007


def collect_clarification_inventory(
    spec_path: Path,
    *,
    review_receipt: Path | None = None,
    prepared_review: PreparedReview | None = None,
    limit: int = 5,
) -> ClarificationInventory:
    """Merge only revalidated review ambiguities, retaining unresolved items beyond the UI cap."""
    from validator.clarify_decisions import apply_recorded_decisions
    from validator.semantic.review_receipts import load_review_receipt

    source_hash = hashlib.sha256(spec_path.read_bytes()).hexdigest()
    deterministic = scan_clarification_opportunities(spec_path)
    semantic: list[ClarifyOpportunity] = []
    complete = False
    errors: list[str] = []
    path = review_receipt or spec_path.parent / ".reviews" / "spec.json"
    if prepared_review is None or not path.is_file():
        errors.append("missing_current_spec_review")
    else:
        try:
            receipt = load_review_receipt(path)
            complete = _current_review(receipt, prepared_review, spec_path)
            if complete:
                if not receipt.ready:
                    errors.append("blocking_spec_review_findings")
                semantic = _review_items(receipt, prepared_review, spec_path, source_hash)
            else:
                errors.append("stale_or_incomplete_spec_review")
        except (OSError, ValueError, ValidationError) as error:
            errors.append(f"invalid_spec_review:{error}")
    inventory = apply_recorded_decisions(spec_path, _merge(deterministic, semantic))
    pending = [item for item in inventory if not item.resolution]
    return ClarificationInventory(
        tuple(inventory),
        tuple(rank_clarification_opportunities(pending, limit=limit)),
        source_hash,
        complete,
        tuple(errors),
    )


def _current_review(receipt: ReviewReceipt, prepared: PreparedReview, spec_path: Path) -> bool:
    """Keep receipt and source checks together without changing short-circuit semantics."""
    from validator.semantic.review_receipts import verify_review_receipt

    complete = verify_review_receipt(receipt, prepared) and receipt.complete
    feature_dir = spec_path.parent
    specs_root = (
        feature_dir.parent.parent if feature_dir.parent.name == "features" else feature_dir.parent
    )
    return complete and prepared_sources_current(
        prepared, feature_dir, specs_root / "constitution.md"
    )
