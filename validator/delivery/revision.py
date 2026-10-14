"""A spec revised during implementation and reviewed once, at the end (feature 089).

Opening records the context hashes of the spec and plan receipts that are current and
ready. While the record exists, the ``implement`` and ``test`` progressions accept those
receipts even though the spec changed; completion and the delivery review wait until
``close`` finds current and ready reviews of the revised sources.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from .review_models import SCHEMA_VERSION, feature_dir, read_json, write_json
from .revision_commit import head_commit, is_ancestor, matches_commit

if TYPE_CHECKING:
    from ..semantic.review_contract import ReviewReceipt

_KINDS: tuple[Literal["spec", "plan"], ...] = ("spec", "plan")


def revision_path(root: Path, feature: str) -> Path:
    """Path of the spec revision record of ``feature``."""
    return feature_dir(root, feature) / ".reviews" / "spec-revision.json"


def read_revision(root: Path, feature: str) -> dict[str, Any] | None:
    """The open revision record, or None; a malformed record raises ValueError."""
    path = revision_path(root, feature)
    if not os.path.lexists(path):
        return None
    record = read_json(path)
    if (
        record is None
        or record.get("feature") != feature
        or not all(isinstance(record.get(kind), str) for kind in _KINDS)
    ):
        raise ValueError(f"malformed spec revision record {path}")
    return record


class RevisionUnverified(ValueError):
    """The open revision record does not match the commit it names (feature 094)."""


# @spec FR-003: Verified acceptance of recorded receipts
#   — .specs/features/094-verified-review-continuity/spec.md#fr-003
def accepted_reviews(root: Path, feature: str) -> frozenset[str]:
    """Context hashes an open revision accepts; empty when no revision is open.

    A recorded receipt still in place is accepted only when the record's commit is an
    ancestor of HEAD and the receipt's reviewed sources at that commit have its stable
    identity; a receipt replaced since opening follows the normal rules.
    """
    from ..semantic.review_files import review_receipt_path
    from ..semantic.review_receipts import load_review_receipt

    record = read_revision(root, feature)
    if record is None:
        return frozenset()
    commit = record.get("commit")
    if not isinstance(commit, str) or not is_ancestor(root, commit):
        raise RevisionUnverified("spec_revision_unverified: no commit of HEAD's history")
    accepted = []
    for kind in _KINDS:
        try:
            receipt = load_review_receipt(review_receipt_path(root, feature, kind))
        except (OSError, ValueError):
            continue
        if receipt.context_hash != record[kind]:
            continue
        if receipt.reviewed is None or not matches_commit(root, commit, receipt.reviewed):
            raise RevisionUnverified(f"spec_revision_unverified: {kind} review at {commit}")
        accepted.append(receipt.context_hash)
    return frozenset(accepted)


def _current(
    root: Path, feature: str, kind: Literal["spec", "plan"], model: str, max_chars: int | None
) -> ReviewReceipt | None:
    """A current and ready receipt of ``kind`` with a reviewed context, else None.

    A receipt without a stored reviewed context (written before 089) is refused: it
    could not stay current once the spec changes.
    """
    from ..semantic.review_files import prepare_feature_review, review_receipt_path
    from ..semantic.review_receipts import load_review_receipt
    from ..semantic.review_stability import reviewed_against

    path = review_receipt_path(root, feature, kind)
    try:
        receipt = load_review_receipt(path)
        prepared = prepare_feature_review(root, feature, kind, model, max_chars)
    except (OSError, ValueError):
        return None
    if receipt.ready and receipt.reviewed and reviewed_against(receipt, prepared) is not None:
        return receipt
    return None


def _reviews(
    root: Path, feature: str, model: str, max_chars: int | None
) -> tuple[dict[str, ReviewReceipt], str]:
    """Both current receipts, or the code naming the first stale one."""
    from ..semantic.review_files import current_review_model

    resolved = current_review_model(root, model)
    receipts: dict[str, ReviewReceipt] = {}
    for kind in _KINDS:
        current = _current(root, feature, kind, resolved, max_chars) if resolved else None
        if current is None:
            return receipts, f"{kind}_review_not_current"
        receipts[kind] = current
    return receipts, ""


# @spec FR-004: Spec revision record
#   — .specs/features/089-stable-review-identity/spec.md#fr-004
def open_revision(
    root: Path, feature: str, model: str = "", max_chars: int | None = None
) -> tuple[dict[str, Any], str]:
    """Record the current reviews; the second value is an error code or ''."""
    if read_revision(root, feature) is not None:
        return {"feature": feature, "open": True}, "spec_revision_open"
    receipts, error = _reviews(root, feature, model, max_chars)
    closed = {"feature": feature, "open": False}
    if error:
        return closed, error
    commit = head_commit(root)
    if commit is None:
        return closed, "spec_revision_unverified"
    if not all(r.reviewed and matches_commit(root, commit, r.reviewed) for r in receipts.values()):
        return closed, "spec_revision_uncommitted"
    record = {
        "schema_version": SCHEMA_VERSION,
        "feature": feature,
        **{kind: receipt.context_hash for kind, receipt in receipts.items()},
        "commit": commit,
        "opened_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    write_json(revision_path(root, feature), record)
    return {**record, "open": True}, ""


def close_revision(
    root: Path, feature: str, model: str = "", max_chars: int | None = None
) -> tuple[dict[str, Any], str]:
    """Remove the record once both reviews are current for the revised sources."""
    if read_revision(root, feature) is None:
        return {"feature": feature, "open": False}, "no_spec_revision"
    _, error = _reviews(root, feature, model, max_chars)
    if error:
        return {"feature": feature, "open": True}, error
    revision_path(root, feature).unlink()
    return {"feature": feature, "open": False}, ""
