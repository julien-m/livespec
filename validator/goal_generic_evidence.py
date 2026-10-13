"""Goal generic evidence responsibilities behind the public contract facade."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from . import goal_contracts as _contracts

__all__ = [
    "_conventions_receipt_missing_items",
    "_required_evidence_satisfied",
    "_validate_generic_evidence",
]

_POLICY_VERIFIED = frozenset(
    {
        "execution_receipt_path",
        "review_receipt_path",
        "acceptance_review_receipt_path",
        "spec_review_receipt_path",
    }
)


def _validate_generic_evidence(
    task: dict[str, Any],
    evidence: dict[str, Any],
    *,
    contract: dict[str, Any],
    project_root: Path | None,
) -> dict[str, Any]:
    missing = _contracts.typed_evidence_missing(
        task, evidence, contract=contract, project_root=project_root
    )
    if not evidence:
        missing.extend(task["required_evidence"])
    for required in cast(list[object], task.get("required_evidence") or []):
        if not isinstance(required, str) or required in _POLICY_VERIFIED:
            continue  # Typed receipts are independently verified by the versioned policy above.
        if required == "conventions_receipt_path":
            missing.extend(
                _contracts._conventions_receipt_missing_items(
                    task, evidence, contract=contract, project_root=project_root
                )
            )
        elif required == "delivery_review_receipt_path":
            missing.extend(
                _delivery_review_missing_items(
                    task, evidence, contract=contract, project_root=project_root
                )
            )
        elif not _contracts._required_evidence_satisfied(required, evidence, project_root):
            missing.append(required)
    accepted = not missing
    return {
        "status": "ACCEPTED" if accepted else "REJECTED_NEEDS_ACTION",
        "accepted": accepted,
        "missing_evidence": missing,
        "invalid_substitutes": [],
        "required_actions": list(task["repair_if_missing"]),
    }


# @spec FR-006: One feature-scope conventions receipt
#   — .specs/features/081-lightweight-outcome-goals/spec.md#fr-006
def _conventions_receipt_missing_items(
    task: Mapping[str, object],
    evidence: Mapping[str, object],
    *,
    contract: Mapping[str, object],
    project_root: Path | None,
) -> list[str]:
    """Validate conventions receipt evidence and return missing proof labels."""
    receipt_path = evidence.get("conventions_receipt_path")
    if not isinstance(receipt_path, str) or not receipt_path.strip():
        return ["conventions_receipt_path"]
    if project_root is None:
        return ["project_root_for_receipt_verification"]
    submitted = Path(receipt_path)
    resolved = (
        submitted.resolve() if submitted.is_absolute() else (project_root / submitted).resolve()
    )
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError:
        return [f"conventions_receipt_valid:path_outside_project:{receipt_path}"]
    expected = task.get("expected_evidence")
    expected_feature = None
    if isinstance(expected, dict) and isinstance(expected.get("feature_slug"), str):
        expected_feature = str(expected["feature_slug"])
    elif isinstance(contract.get("feature"), str):
        expected_feature = str(contract["feature"])
    try:
        receipt = _contracts.verify_conventions_receipt(
            resolved,
            project_root=project_root,
            expected_feature_slug=expected_feature,
        )
    except (OSError, _contracts.ConventionsReceiptError) as exc:
        return [f"conventions_receipt_valid:{exc}"]
    if receipt.verdict != "PASS":
        return ["conventions_receipt_verdict_pass"]
    return []


# @spec FR-007: The goal re-verifies the delivery review receipt
#   — .specs/features/086-risk-proportional-delivery/spec.md#fr-007
def _delivery_review_missing_items(
    task: Mapping[str, object],
    evidence: Mapping[str, object],
    *,
    contract: Mapping[str, object],
    project_root: Path | None,
) -> list[str]:
    """Accept the receipt only when `livespec delivery review verify` would pass now."""
    from .delivery.lane import DeliveryInputError, evaluate_lane
    from .delivery.review import receipt_path, verify_review

    submitted = evidence.get("delivery_review_receipt_path")
    if not isinstance(submitted, str) or not submitted.strip():
        return ["delivery_review_receipt_path"]
    if project_root is None:
        return ["project_root_for_receipt_verification"]
    expected = task.get("expected_evidence")
    expected_map = cast(dict[str, object], expected) if isinstance(expected, dict) else {}
    feature = expected_map.get("feature_slug") or contract.get("feature")
    if not isinstance(feature, str) or not feature:
        return ["delivery_review_feature"]
    root = project_root.resolve()
    try:
        canonical = receipt_path(root, feature).resolve()
        given = Path(submitted)
        resolved = (given if given.is_absolute() else root / given).resolve()
        if resolved != canonical:
            return [f"delivery_review_receipt_valid:not_the_feature_receipt:{submitted}"]
        model = expected_map.get("reviewer_model")
        budget = expected_map.get("review_max_chars")
        lane = evaluate_lane(
            root,
            feature,
            model if isinstance(model, str) else "",
            budget if isinstance(budget, int) else None,
        ).lane
        outcome = verify_review(root, feature, lane)
    except DeliveryInputError as exc:
        return [f"delivery_review_receipt_valid:{exc}"]
    return [f"delivery_review_receipt_valid:{reason.code}" for reason in outcome.reasons]


def _required_evidence_satisfied(
    required: str,
    evidence: dict[str, Any],
    project_root: Path | None,
) -> bool:
    if required == "observable_output_or_artifact":
        return bool(evidence.get("output")) or _contracts._any_evidence_path_exists(
            evidence, ("artifact", "path", "paths", "files"), project_root
        )
    if required == "success_criteria_met":
        return evidence.get("success_criteria_met") is True
    # Historical (pre-081) boolean proof items keep their original meaning.
    return evidence.get(required) is True
