"""Shared immutable archive receipt-check records."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReceiptCheck:
    """Integrity re-verification result for one referenced receipt."""

    kind: str
    path: str
    verified: bool
    verdict: str | None
    error: str | None
    reviewer_model: str = ""
    review_max_chars: int | None = None
    expected_outcome: str = ""
    evidence_policy: str = "2"
    review_kind: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable ``receipts[]`` artifact entry."""
        return {
            "kind": self.kind,
            "path": self.path,
            "verified": self.verified,
            "verdict": self.verdict,
            "error": self.error,
            **({"reviewer_model": self.reviewer_model} if self.reviewer_model else {}),
            **({"review_max_chars": self.review_max_chars} if self.review_max_chars else {}),
            **({"expected_outcome": self.expected_outcome} if self.expected_outcome else {}),
            **({"evidence_policy": self.evidence_policy} if self.kind == "execution" else {}),
            **({"review_kind": self.review_kind} if self.review_kind else {}),
        }


def archived_review_kinds(artifact: dict[str, Any]) -> dict[str, str]:
    """Derive new review obligations from canonical tasks, never receipt-entry mirrors."""
    canonical = _object(_object(artifact.get("evidence_contract")).get("canonical"))
    declarations = canonical.get("tasks", [])
    states = {
        str(row.get("id")): row
        for row in _object(artifact.get("goal")).get("tasks", [])
        if isinstance(row, dict)
    }
    result: dict[str, str] = {}
    for declaration in declarations if isinstance(declarations, list) else []:
        declared = _object(declaration)
        expected = _object(declared.get("expected_evidence")).get("review_kind")
        if expected is None:
            continue  # Explicit historical branch; never invent an obligation for old contracts.
        state = states.get(str(declared.get("id")), {})
        path = _object(state.get("accepted_evidence")).get("review_receipt_path")
        if isinstance(path, str):
            value = str(expected)
            result[path] = value if result.get(path, value) == value else "conflicting_review_kinds"
    return result


def _object(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
