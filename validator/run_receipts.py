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

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from .conventions_receipt import ConventionsReceiptError, verify_conventions_receipt
from .finalize_receipt import FinalizeReceiptError, verify_finalize_receipt
from .visual_evidence import VisualReceiptError, verify_visual_receipt

# Evidence keys that reference verifiable receipts, mapped to receipt kinds.
_RECEIPT_EVIDENCE_KEYS: tuple[tuple[str, str], ...] = (
    ("finalize_receipt_path", "finalize"),
    ("visual_evidence_receipt_path", "visual"),
    ("conventions_receipt_path", "conventions"),
)


@dataclass(frozen=True)
class ReceiptCheck:
    """Integrity re-verification result for one referenced receipt."""

    kind: str
    path: str
    verified: bool
    verdict: str | None
    error: str | None

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable ``receipts[]`` artifact entry."""
        return {
            "kind": self.kind,
            "path": self.path,
            "verified": self.verified,
            "verdict": self.verdict,
            "error": self.error,
        }


def verify_evidence_receipts(
    tasks: list[dict[str, Any]],
    *,
    project_root: Path,
    feature: str | None,
) -> list[ReceiptCheck]:
    """Collect and re-verify every receipt referenced by accepted evidence."""
    checks: list[ReceiptCheck] = []
    seen: set[tuple[str, str]] = set()
    for task in tasks:
        evidence = task.get("accepted_evidence")
        if not isinstance(evidence, dict):
            continue
        evidence_map = cast(dict[str, Any], evidence)
        for key, kind in _RECEIPT_EVIDENCE_KEYS:
            path_value = evidence_map.get(key)
            if not isinstance(path_value, str) or not path_value:
                continue
            ref = (kind, path_value)
            if ref in seen:
                continue
            seen.add(ref)
            checks.append(
                verify_one_receipt(
                    kind=kind,
                    path=path_value,
                    project_root=project_root,
                    feature=feature,
                )
            )
    return checks


def recheck_receipts(
    receipt_entries: list[dict[str, Any]],
    *,
    project_root: Path,
    feature: str | None,
) -> list[ReceiptCheck]:
    """Re-verify receipt integrity from archived ``receipts[]`` entries.

    Used by ``verify-output`` to re-check the chain of proof at read time
    (same semantics as archive time: integrity only, feature scope iff
    ``feature`` is given).
    """
    return [
        verify_one_receipt(
            kind=str(entry.get("kind", "")),
            path=str(entry.get("path", "")),
            project_root=project_root,
            feature=feature,
        )
        for entry in receipt_entries
    ]


# @spec FR-004: receipt integrity re-verification
#   — .specs/features/039.1-goal-archive-run-artifacts/spec.md#fr-004
def verify_one_receipt(
    *,
    kind: str,
    path: str,
    project_root: Path,
    feature: str | None,
) -> ReceiptCheck:
    """Integrity-only re-verification of one finalize/visual/conventions receipt.

    ``expected_command`` is never checked (receipts are frequently emitted by
    child commands); ``expected_feature_slug`` is checked only when the caller
    scoped the run with ``--feature`` (AC-006, EC-008).
    """
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
        if kind == "conventions":
            verdict = str(
                verify_conventions_receipt(
                    receipt_path,
                    project_root=project_root,
                    expected_feature_slug=feature,
                ).verdict
            )
        elif kind == "visual":
            verdict = str(
                verify_visual_receipt(
                    receipt_path,
                    project_root=project_root,
                    expected_feature_slug=feature,
                    expected_command=None,
                ).verdict
            )
        else:
            verdict = str(
                verify_finalize_receipt(
                    receipt_path,
                    project_root=project_root,
                    expected_feature_slug=feature,
                    expected_command=None,
                ).verdict
            )
    except (ConventionsReceiptError, FinalizeReceiptError, VisualReceiptError) as exc:
        return ReceiptCheck(kind=kind, path=path, verified=False, verdict=None, error=str(exc))
    return ReceiptCheck(
        kind=kind,
        path=path,
        verified=True,
        verdict=verdict,
        error=None,
    )


__all__ = ["ReceiptCheck", "recheck_receipts", "verify_evidence_receipts", "verify_one_receipt"]
