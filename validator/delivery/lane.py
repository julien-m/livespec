"""Light or full delivery lane from the QE risk classification (feature 086 FR-002, FR-003)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ..identity import SLUG_REGEX

Lane = Literal["light", "full"]

_LIGHT_CRITICALITY = frozenset({"low", "medium"})
_LIGHT_BLAST_RADIUS = frozenset({"local", "shared"})
# A value must end at a delimiter: "Medium-High" is not "Medium".
_CRITICALITY = r"(low|medium|high)(?![\w-])"
_BLAST_RADIUS = r"(local|shared|cross-system|external)(?![\w-])"
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,}).*?^ {0,3}\1[^\S\n]*$", re.MULTILINE | re.DOTALL)
# Forms used by existing specs: prose ("High criticality; Shared blast radius"),
# bold labels ("**Criticality:** High") and table rows ("| Criticality | High |").
_CRITICALITY_PATTERNS = (
    re.compile(rf"\b{_CRITICALITY}\s+criticality\b", re.IGNORECASE),
    re.compile(rf"criticality\s*(?::\s*\*\*|\*\*\s*:|:|\|)\s*\**\s*{_CRITICALITY}\b", re.I),
)
_BLAST_PATTERNS = (
    re.compile(rf"\b{_BLAST_RADIUS}\s+blast\s+radius\b", re.IGNORECASE),
    re.compile(rf"blast\s+radius\s*(?::\s*\*\*|\*\*\s*:|:|\|)\s*\**\s*{_BLAST_RADIUS}\b", re.I),
)
_DECLARED_FULL = re.compile(r"\*\*delivery lane:\*\*\s*full\b", re.IGNORECASE)
_QE_HEADING = re.compile(r"^(#{2,3})\s+Quality Engineering\b.*$", re.MULTILINE | re.IGNORECASE)


class DeliveryInputError(ValueError):
    """A command argument cannot be used (unknown feature, unreadable spec)."""


@dataclass(frozen=True)
class LaneReason:
    """One condition that keeps the feature in the full lane."""

    code: str
    detail: str


@dataclass
class LaneDecision:
    """Outcome of one lane evaluation; no reason means the light lane."""

    feature: str
    criticality: str | None = None
    blast_radius: str | None = None
    reasons: list[LaneReason] = field(default_factory=lambda: list[LaneReason]())

    @property
    def lane(self) -> Lane:
        """Return ``light`` only when no condition requires the full lane."""
        return "full" if self.reasons else "light"

    def to_json(self) -> dict[str, object]:
        """Return the AC-001 JSON object."""
        return {
            "feature": self.feature,
            "lane": self.lane,
            "criticality": self.criticality,
            "blast_radius": self.blast_radius,
            "reasons": [{"code": r.code, "detail": r.detail} for r in self.reasons],
        }


def qe_section(spec_text: str) -> str | None:
    """Return the body of the only ``Quality Engineering`` section, or None.

    Fenced code blocks are ignored, so an example cannot select or end the section.
    """
    spec_text = _FENCE.sub("", spec_text)
    match = _QE_HEADING.search(spec_text)
    if match is None:
        return None
    level = len(match.group(1))
    rest = spec_text[match.end() :]
    # The section ends at the next heading of the same or a higher level.
    end = re.search(rf"^#{{1,{level}}}\s", rest, flags=re.MULTILINE)
    return rest[: end.start()] if end else rest


def _values(section: str, patterns: tuple[re.Pattern[str], ...], value: str) -> set[str]:
    """Every value of a field; any other value word on a field line counts as a conflict."""
    found: set[str] = set()
    word = re.compile(rf"\b{value}", re.IGNORECASE)
    for line in section.splitlines():
        if any(pattern.search(line) for pattern in patterns):
            found.update(m.group(1).lower() for m in word.finditer(line))
    return found


# @spec FR-002: QE classification and lane rule
#   — .specs/features/086-risk-proportional-delivery/spec.md#fr-002
def classify(feature: str, spec_text: str) -> LaneDecision:
    """Parse the QE classification and collect every full-lane reason except review currency."""
    decision = LaneDecision(feature)
    section = qe_section(spec_text)
    if len(_QE_HEADING.findall(_FENCE.sub("", spec_text))) > 1:
        decision.reasons.append(
            LaneReason("qe_classification_conflicting", "several Quality Engineering sections")
        )
    if section is None:
        decision.reasons.append(
            LaneReason("qe_section_missing", "spec.md has no 'Quality Engineering' section")
        )
        return decision
    for name, patterns, light, value_pattern in (
        ("criticality", _CRITICALITY_PATTERNS, _LIGHT_CRITICALITY, _CRITICALITY),
        ("blast_radius", _BLAST_PATTERNS, _LIGHT_BLAST_RADIUS, _BLAST_RADIUS),
    ):
        found = _values(section, patterns, value_pattern)
        if not found:
            decision.reasons.append(LaneReason(f"{name}_missing", f"no {name} value in QE"))
            continue
        if len(found) > 1:
            decision.reasons.append(
                LaneReason("qe_classification_conflicting", f"{name}: {', '.join(sorted(found))}")
            )
            continue
        value = next(iter(found))
        setattr(decision, name, value)
        if value not in light:
            code = "criticality_high" if name == "criticality" else "blast_radius_wide"
            decision.reasons.append(LaneReason(code, f"{name} is {value}"))
    if _DECLARED_FULL.search(section):
        decision.reasons.append(LaneReason("declared_full", "QE declares **Delivery lane:** full"))
    return decision


# @spec FR-003: Reviewed classification only
#   — .specs/features/086-risk-proportional-delivery/spec.md#fr-003
def spec_review_current(
    project_root: Path, feature: str, model: str = "", max_chars: int | None = None
) -> tuple[bool, str]:
    """Return whether the spec review receipt is current and ready, with a detail.

    Reads sources and the receipt only; never calls a reviewer.
    """
    from ..semantic.review_files import (
        current_review_model,
        prepare_feature_review,
        review_receipt_path,
    )
    from ..semantic.review_receipts import load_review_receipt, verify_review_receipt

    resolved = current_review_model(project_root, model)
    if not resolved:
        return False, "reviewer model unresolved (pass --model or configure review_model)"
    receipt_path = review_receipt_path(project_root, feature, "spec")
    if not receipt_path.is_file():
        return False, f"no spec review receipt at {receipt_path.relative_to(project_root)}"
    try:
        prepared = prepare_feature_review(project_root, feature, "spec", resolved, max_chars)
        receipt = load_review_receipt(receipt_path)
    except (OSError, ValueError) as exc:
        return False, f"spec review unreadable: {exc}"
    if not verify_review_receipt(receipt, prepared):
        return False, f"spec review is stale or incomplete for model {resolved}"
    if not receipt.ready:
        return False, "spec review is not ready"
    return True, "current"


def evaluate_lane(
    project_root: Path, feature: str, model: str = "", max_chars: int | None = None
) -> LaneDecision:
    """Evaluate the lane of an existing feature.

    Raises:
        DeliveryInputError: Unknown feature or unreadable spec.
    """
    spec = project_root / ".specs" / "features" / feature / "spec.md"
    if not SLUG_REGEX.fullmatch(feature) or not spec.is_file():
        raise DeliveryInputError(f"unknown feature {feature!r}")
    try:
        text = spec.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise DeliveryInputError(f"unreadable spec {spec}: {exc}") from exc
    decision = classify(feature, text)
    current, detail = spec_review_current(project_root, feature, model, max_chars)
    if not current:
        decision.reasons.append(LaneReason("spec_review_not_current", detail))
    return decision
