"""Confined semantic and execution receipt verification at archive boundaries."""

from pathlib import Path
from typing import Literal

from .run_receipt_types import ReceiptCheck


def verify_requirement_receipt(
    kind: str,
    path: str,
    root: Path,
    feature: str | None,
    reviewer_model: str = "",
    review_max_chars: int | None = None,
    expected_outcome: str = "",
    evidence_policy: str = "2",
    review_kind: str | None = None,
) -> ReceiptCheck:
    """Recheck typed receipts at archive and later consumption boundaries."""
    try:
        selected = _requirement_receipt_path(path, root, feature)
        valid, error = _requirement_result(
            selected,
            root,
            feature or "",
            kind,
            reviewer_model,
            review_max_chars,
            expected_outcome,
            evidence_policy,
            review_kind,
        )
        return ReceiptCheck(
            kind,
            path,
            valid,
            "PASS" if valid else "BLOCKED",
            error or None,
            reviewer_model,
            review_max_chars,
            expected_outcome,
            evidence_policy,
            review_kind,
        )
    except (OSError, ValueError, TypeError) as exc:
        return ReceiptCheck(kind, path, False, None, str(exc))


def _requirement_receipt_path(path: str, root: Path, feature: str | None) -> Path:
    """Require a declared feature and a project-confined receipt before consuming it."""
    if not feature:
        raise ValueError("receipt_feature_required")
    selected = Path(path)
    selected = selected if selected.is_absolute() else root / selected
    selected.resolve().relative_to(root.resolve())
    return selected


def _semantic_review_result(
    selected: Path,
    root: Path,
    feature: str,
    model: str,
    max_chars: int | None,
    review_kind: str | None,
) -> tuple[bool, str]:
    """Verify a semantic receipt against the immutable declaration's purpose."""
    from .semantic.review_api import verify_feature_review

    if review_kind not in (None, "spec", "plan"):
        raise ValueError("unknown_review_kind")
    expected_kind: Literal["spec", "plan"] | None = (
        None if review_kind is None else ("spec" if review_kind == "spec" else "plan")
    )
    valid = verify_feature_review(
        root, feature, selected, model=model, max_chars=max_chars, expected_kind=expected_kind
    )
    return valid, "" if valid else "review_receipt_incomplete_or_stale"


def _acceptance_review_result(
    selected: Path,
    root: Path,
    feature: str,
    model: str,
    max_chars: int | None,
) -> tuple[bool, str]:
    """Keep documentary acceptance review separate from semantic progression review."""
    from .semantic.acceptance_review import verify_acceptance_review

    valid = verify_acceptance_review(root, feature, selected, model=model, max_chars=max_chars)
    return valid, "" if valid else "acceptance_review_incomplete_or_stale"


def _execution_receipt_result(
    selected: Path, root: Path, feature: str, outcome: str, policy: str
) -> tuple[bool, str]:
    from .execution_evidence import verify_execution_observation, verify_execution_receipt

    if policy not in ("1", "2"):
        raise ValueError("unknown_evidence_policy_version")
    if outcome == "red":
        result = verify_execution_observation(
            selected, root, feature, "red", evidence_policy="1" if policy == "1" else "2"
        )
    else:
        result = verify_execution_receipt(
            selected,
            project_root=root,
            feature=feature,
            evidence_policy="1" if policy == "1" else "2",
        )
    return result.valid, ";".join(result.gaps)


def _requirement_result(
    selected: Path,
    root: Path,
    feature: str,
    kind: str,
    model: str,
    max_chars: int | None,
    outcome: str,
    policy: str,
    review_kind: str | None,
) -> tuple[bool, str]:
    if kind == "execution":
        return _execution_receipt_result(selected, root, feature, outcome, policy)
    if kind == "acceptance_review":
        return _acceptance_review_result(selected, root, feature, model, max_chars)
    return _semantic_review_result(selected, root, feature, model, max_chars, review_kind)
