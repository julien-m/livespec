"""Requirement definition extraction and cited-requirement scope (feature 084 FR-004, FR-008)."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import ValidationError

from ..semantic.review_contract import ReviewReceipt
from .models import FallbackReason

# A definition line starts, after optional list, heading, table-cell or bold markup,
# with FR-NNN, AC-NNN or SC-NNN: "- **FR-001:** ...", "### AC-002", "| SC-003 | ...".
_DEFINITION = re.compile(r"^\s*(?:[-*+]\s+|#{1,6}\s+|\|\s*)?(?:\*\*)?((?:FR|AC|SC)-\d{3})\b")
_HEADING = re.compile(r"^\s*#{1,6}\s")
_REQUIREMENT_ID = re.compile(r"^(?:FR|AC|SC)-\d{3}$")
_AMBIGUITY_MARKERS = ("[NEEDS CLARIFICATION", "[DECISION NEEDED")
# Fenced ```gherkin blocks: the body between the opening fence line and the closing fence.
_GHERKIN = re.compile(r"^\s*```gherkin[^\n]*\n(.*?)^\s*```", re.MULTILINE | re.DOTALL)


# @spec FR-004: Requirement definition extraction
#   — .specs/features/084-bugfix-lane/spec.md#fr-004
def requirement_definitions(text: str) -> dict[str, str]:
    """Map each FR/AC/SC identifier to its whitespace-normalized definition block.

    A heading definition extends to the next heading; any other definition extends
    to the next blank line, heading or definition (plan D-01). Repeated identifiers
    are concatenated so a duplicate edit is still detected.
    """
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    heading_block = False
    for line in text.splitlines():
        match = _DEFINITION.match(line)
        if match:
            identifier = match.group(1)
            current = identifier
            heading_block = bool(_HEADING.match(line))
            blocks.setdefault(identifier, []).append(line)
            continue
        is_boundary = bool(_HEADING.match(line)) or (not heading_block and not line.strip())
        if is_boundary:
            current = None
        elif current is not None:
            blocks[current].append(line)
    return {key: " ".join(" ".join(lines).split()) for key, lines in blocks.items()}


def gherkin_blocks(text: str) -> list[str]:
    """Return the whitespace-normalized content of every fenced gherkin block, in order."""
    return [" ".join(block.split()) for block in _GHERKIN.findall(text)]


def changed_requirements(before: str | None, after: str | None) -> list[str]:
    """Return identifiers added, removed or changed, plus `Gherkin scenarios` on any change."""
    old = requirement_definitions(before or "")
    new = requirement_definitions(after or "")
    changed = sorted(key for key in old.keys() | new.keys() if old.get(key) != new.get(key))
    if gherkin_blocks(before or "") != gherkin_blocks(after or ""):
        changed.append("Gherkin scenarios")
    return changed


# @spec FR-008: Cited requirement scope
#   — .specs/features/084-bugfix-lane/spec.md#fr-008
def requirement_scope_reasons(
    project_root: Path, feature: str, cited: tuple[str, ...]
) -> list[FallbackReason]:
    """Check only the cited requirements; read the review receipt only when one is cited."""
    if not cited:
        return []
    spec = project_root / ".specs" / "features" / feature / "spec.md"
    definitions = requirement_definitions(spec.read_text(encoding="utf-8"))
    reasons: list[FallbackReason] = []
    for requirement in cited:
        text = definitions.get(requirement)
        if not _REQUIREMENT_ID.match(requirement) or text is None:
            reasons.append(FallbackReason("requirement_unknown", f"{requirement} not in {spec}"))
        elif any(marker in text for marker in _AMBIGUITY_MARKERS):
            reasons.append(FallbackReason("requirement_ambiguous", f"{requirement} is marked"))
    receipt_path = spec.parent / ".reviews" / "spec.json"
    if not receipt_path.exists():
        return reasons
    try:
        receipt = ReviewReceipt.model_validate_json(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError) as exc:
        # Treating an unreadable receipt as absent would silently drop its findings.
        reasons.append(FallbackReason("review_receipt_unreadable", f"{receipt_path}: {exc}"))
        return reasons
    for requirement in cited:
        reasons.extend(_concerning(receipt, feature, requirement))
    return reasons


def _concerning(receipt: ReviewReceipt, feature: str, requirement: str) -> list[FallbackReason]:
    qualified = f"{feature}:{requirement}"
    token = re.compile(rf"\b{re.escape(requirement)}\b")
    details: list[str] = [
        f"conclusion {c.disposition}"
        for c in receipt.conclusions
        if c.requirement_id in (qualified, requirement) and c.disposition != "covered"
    ]
    details += [
        f"critical ambiguity {a.decision_key}"
        for a in receipt.ambiguities
        if a.requirement_id in (qualified, requirement) and a.critical and not a.resolution
    ]
    details += [
        f"blocking finding {f.category}"
        for f in receipt.findings
        if f.severity == "blocking"
        and (
            token.search(f.description)
            or any(token.search(citation.excerpt) for citation in f.citations)
        )
    ]
    return [FallbackReason("requirement_blocking_finding", f"{requirement}: {d}") for d in details]
