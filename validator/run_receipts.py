# @spec(FR-001)
# @spec(FR-002)

# LiveSpec traceability anchors
# @spec(AC-006)

"""Receipt integrity re-verification for RunArtifact v2 archives.

Private helper module for :mod:`validator.run_artifacts` (kept separate to
honor the 300-line constitution cap — same precedent as
``finalize_receipt.py``). The public API is re-exported from
``validator.run_artifacts``; import from there, not from here.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from .conventions_receipt import ConventionsReceiptError, verify_conventions_receipt
from .finalize_receipt import FinalizeReceiptError, verify_finalize_receipt
from .run_receipt_types import ReceiptCheck
from .run_requirement_receipts import verify_requirement_receipt
from .visual_evidence import VisualReceiptError, verify_visual_receipt

# Evidence keys that reference verifiable receipts, mapped to receipt kinds.
_RECEIPT_EVIDENCE_KEYS: tuple[tuple[str, str], ...] = (
    ("finalize_receipt_path", "finalize"),
    ("visual_evidence_receipt_path", "visual"),
    ("conventions_receipt_path", "conventions"),
    ("execution_receipt_path", "execution"),
    ("review_receipt_path", "review"),
    ("acceptance_review_receipt_path", "acceptance_review"),
)


def verify_evidence_receipts(
    tasks: list[dict[str, Any]],
    *,
    project_root: Path,
    feature: str | None,
    requirement_feature: str | None = None,
    reviewer_model: str = "",
    review_max_chars: int | None = None,
    evidence_policy: str = "2",
) -> list[ReceiptCheck]:
    """Collect unique receipt obligations and re-verify them without changing evidence.

    Args:
        tasks: Validated tasks with accepted evidence and canonical expected metadata.
        project_root: Root for receipt confinement and current-source verification.
        feature: Optional feature constraint for finalize, visual and conventions.
        requirement_feature: Typed-receipt feature override; falls back to feature.
        reviewer_model: Semantic/acceptance reviewer identity; empty resolves configuration.
        review_max_chars: Review context budget; None uses configured policy.
        evidence_policy: Execution policy selected by the contract: historical 1 or current 2.
    Returns:
        ReceiptCheck list deduplicated by family, path, outcome and canonical review kind.
    Raises:
        OSError: Unwrapped specialized-validator reads; see verify_one_receipt.
        ValueError: Unwrapped specialized validation/decoding errors.
        TypeError: Invalid inputs outside the typed-receipt error boundary.
        AttributeError: Malformed task metadata instead of the declared mapping shape.
    Side effects:
        Reads receipts and their current inputs; writes nothing and never executes tests.
    """
    return _collect_evidence_receipts(
        tasks,
        project_root=project_root,
        feature=feature,
        requirement_feature=requirement_feature,
        reviewer_model=reviewer_model,
        review_max_chars=review_max_chars,
        evidence_policy=evidence_policy,
    )


def _collect_evidence_receipts(
    tasks: list[dict[str, Any]],
    *,
    project_root: Path,
    feature: str | None,
    requirement_feature: str | None = None,
    reviewer_model: str = "",
    review_max_chars: int | None = None,
    evidence_policy: str = "2",
) -> list[ReceiptCheck]:
    """Collect and re-verify every receipt referenced by accepted evidence."""
    checks: list[ReceiptCheck] = []
    seen: set[tuple[str, str, str, str | None]] = set()
    for task in tasks:
        evidence = task.get("accepted_evidence")
        if not isinstance(evidence, dict):
            continue
        evidence_map = cast(dict[str, Any], evidence)
        for key, kind in _RECEIPT_EVIDENCE_KEYS:
            path_value = evidence_map.get(key)
            if not isinstance(path_value, str) or not path_value:
                continue
            expected_outcome = str(task.get("evidence_expected_outcome", ""))
            review_kind = task.get("expected_evidence", {}).get("review_kind")
            review_kind = str(review_kind) if review_kind is not None else None
            ref = (kind, path_value, expected_outcome, review_kind)
            if ref in seen:
                continue
            seen.add(ref)
            checks.append(
                verify_one_receipt(
                    kind=kind,
                    path=path_value,
                    project_root=project_root,
                    feature=(requirement_feature or feature)
                    if kind in {"execution", "review", "acceptance_review"}
                    else feature,
                    reviewer_model=reviewer_model,
                    review_max_chars=review_max_chars,
                    expected_outcome=expected_outcome,
                    evidence_policy=evidence_policy,
                    review_kind=review_kind,
                )
            )
    return checks


def recheck_receipts(
    receipt_entries: list[dict[str, Any]],
    *,
    project_root: Path,
    feature: str | None,
    requirement_feature: str | None = None,
    evidence_policy: str = "1",
    expected_review_kinds: Mapping[str, str] | None = None,
) -> list[ReceiptCheck]:
    """Re-verify archive entries against canonical obligations, preserving historical absence.

    Args:
        receipt_entries: Archived receipt entries, including model, budget and outcome.
        project_root: Root for receipt confinement and current-source verification.
        feature: Optional feature constraint for finalize, visual and conventions.
        requirement_feature: Typed-receipt feature override; falls back to feature.
        evidence_policy: Historical execution fallback 1; an entry's explicit policy wins.
        expected_review_kinds: Canonical path-to-kind map; undeclared paths retain either-kind.
    Returns:
        Checks in entry order, then failures for absent mandatory review entries.
        Missing or changed kind mirrors fail; other failures follow verify_one_receipt.
    Raises:
        OSError: Unwrapped specialized-validator reads.
        ValueError: Unwrapped specialized validation/decoding errors.
        TypeError: Invalid inputs outside the typed-receipt error boundary.
        AttributeError: Malformed entries instead of the declared mapping shape.
    Side effects:
        Reads receipts and their current inputs; writes nothing and never executes tests.
    """
    expected = expected_review_kinds or {}
    checks = [
        _recheck_entry(
            entry,
            project_root,
            feature,
            requirement_feature,
            evidence_policy,
            expected.get(str(entry.get("path", ""))),
        )
        for entry in receipt_entries
    ]
    present = {str(entry.get("path")) for entry in receipt_entries if entry.get("kind") == "review"}
    checks.extend(
        ReceiptCheck("review", path, False, None, "review_kind_receipt_missing")
        for path in expected
        if path not in present
    )
    return checks


def _recheck_entry(
    entry: dict[str, Any],
    root: Path,
    feature: str | None,
    requirement_feature: str | None,
    policy: str,
    expected_kind: str | None,
) -> ReceiptCheck:
    kind, path = str(entry.get("kind", "")), str(entry.get("path", ""))
    if kind == "review" and expected_kind is not None and entry.get("review_kind") != expected_kind:
        return ReceiptCheck(kind, path, False, None, "review_kind_mirror_mismatch")
    return verify_one_receipt(
        kind=kind,
        path=path,
        project_root=root,
        feature=(requirement_feature or feature)
        if kind in {"execution", "review", "acceptance_review"}
        else feature,
        reviewer_model=str(entry.get("reviewer_model", "")),
        review_max_chars=entry.get("review_max_chars"),
        expected_outcome=str(entry.get("expected_outcome", "")),
        evidence_policy=str(entry.get("evidence_policy", policy)),
        review_kind=expected_kind,
    )


# @spec FR-004: receipt integrity re-verification
#   — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-004
def verify_one_receipt(
    *,
    kind: str,
    path: str,
    project_root: Path,
    feature: str | None,
    reviewer_model: str = "",
    review_max_chars: int | None = None,
    expected_outcome: str = "",
    evidence_policy: str = "2",
    review_kind: str | None = None,
) -> ReceiptCheck:
    """Re-verify one receipt's integrity without requiring a producing command identity.

    Args:
        kind: finalize, visual, conventions, execution, review or acceptance_review.
        path: Absolute or project-relative receipt path.
        project_root: Root for receipt confinement and current-source verification.
        feature: Required typed-receipt feature; optional constraint for other families.
        reviewer_model: Semantic/acceptance reviewer identity; empty resolves configuration.
        review_max_chars: Review context budget; None uses configured policy.
        expected_outcome: Execution only: red observes failure; all other values require pass.
        evidence_policy: Execution only: immutable historical 1 or current 2; unknown fails.
        review_kind: Canonical semantic purpose spec/plan; None retains historical either-kind.
    Returns:
        Integrity check and verdict; a verified specialized verdict may still be FAIL/BLOCKED.
        Unknown kinds and ConventionsReceiptError/FinalizeReceiptError/VisualReceiptError
        produce failed checks. Typed OSError/ValueError/TypeError also become failed checks;
        unrelated errors propagate.
    Raises:
        OSError: Unwrapped specialized-validator reads.
        ValueError: Unwrapped specialized validation/decoding errors.
        TypeError: Invalid inputs outside the typed-receipt error boundary.
    Side effects:
        Reads receipts, current sources and referenced images; writes nothing and runs no tests.
    """
    if kind in {"execution", "review", "acceptance_review"}:
        return verify_requirement_receipt(
            kind,
            path,
            project_root,
            feature,
            reviewer_model,
            review_max_chars,
            expected_outcome,
            evidence_policy,
            review_kind,
        )
    return _verify_specialized_receipt(kind, path, project_root, feature)


def _verify_specialized_receipt(
    kind: str, path: str, project_root: Path, feature: str | None
) -> ReceiptCheck:
    if kind not in {"finalize", "visual", "conventions"}:
        return ReceiptCheck(
            kind=kind,
            path=path,
            verified=False,
            verdict=None,
            error=f"unknown receipt kind: {kind}",
        )
    receipt_path = Path(path)
    try:
        verdict = _specialized_verdict(kind, receipt_path, project_root, feature)
    except (ConventionsReceiptError, FinalizeReceiptError, VisualReceiptError) as exc:
        return ReceiptCheck(kind=kind, path=path, verified=False, verdict=None, error=str(exc))
    return ReceiptCheck(
        kind=kind,
        path=path,
        verified=True,
        verdict=verdict,
        error=None,
    )


def _specialized_verdict(kind: str, path: Path, root: Path, feature: str | None) -> str:
    if kind == "conventions":
        return str(
            verify_conventions_receipt(
                path, project_root=root, expected_feature_slug=feature
            ).verdict
        )
    verifier = verify_visual_receipt if kind == "visual" else verify_finalize_receipt
    return str(
        verifier(
            path, project_root=root, expected_feature_slug=feature, expected_command=None
        ).verdict
    )


__all__ = ["ReceiptCheck", "recheck_receipts", "verify_evidence_receipts", "verify_one_receipt"]
