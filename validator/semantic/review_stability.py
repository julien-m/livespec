"""Spec and plan reviews stay current until the requirements they judged change (feature 089).

A receipt stores the context it was validated against. When the current context hash
differs, the receipt is still current if that reviewed context has the same stable
identity as the current preparation and its raw results rebuild against it exactly.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING

from validator.normative_identity import normative_hash

if TYPE_CHECKING:
    from validator.semantic.review_context import PreparedReview
    from validator.semantic.review_contract import ReviewReceipt

_FENCE = re.compile(r"^\s*(`{3,}|~{3,})\s*(\S*)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_REQUIREMENT_SECTIONS = ("functional requirements", "acceptance criteria")
_REQUIREMENT_ID = re.compile(r"\b(?:FR|AC)-\d+\b")
# A requirement defined outside its section: "- **FR-001:** ..." or "**AC-002** ...".
_DEFINITION = re.compile(r"^\s*(?:[-*]\s+)?\*\*(?:FR|AC)-\d+\b")


def reviewed_snapshot(prepared: PreparedReview) -> PreparedReview:
    """The prepared context without its prompts, stamped with the running protocol versions.

    Validation never reads the prompts; the versions are those in force now, so a protocol
    release changes the stable identity like it changes the context hash.
    """
    from validator.semantic import review_context as context

    batches = tuple(batch.model_copy(update={"prompt": ""}) for batch in prepared.batches)
    return prepared.model_copy(
        update={
            "batches": batches,
            "policy_version": context.POLICY_VERSION,
            "schema_version": context.SCHEMA_VERSION,
            "prompt_version": context.PROMPT_VERSION,
        }
    )


def _normalized(line: str) -> str:
    return " ".join(re.sub(r"[*`]", "", line).split())


# @spec FR-002: Requirement projection and stable identity
#   — .specs/features/089-stable-review-identity/spec.md#fr-002
def requirement_projection(text: str) -> str:
    """FR and AC sections, FR/AC definitions and Gherkin blocks, without emphasis or spacing.

    A requirement section is a ``Functional Requirements`` or ``Acceptance Criteria``
    heading, or a heading naming an FR or AC id, with everything below it until the next
    heading of the same or a higher level.
    """
    kept: list[str] = []
    level = 0  # Heading level of the requirement section being read, 0 outside.
    fence = ""
    gherkin = False
    for line in text.splitlines():
        opening = _FENCE.match(line)
        if fence:
            if opening and opening.group(1)[0] == fence[0] and len(opening.group(1)) >= len(fence):
                fence, gherkin = "", False
            elif level or gherkin:
                kept.append(_normalized(line))
            continue
        if opening:
            fence, gherkin = opening.group(1), opening.group(2).lower() == "gherkin"
            continue
        heading = _HEADING.match(line)
        if heading:
            depth = len(heading.group(1))
            if level and depth <= level:
                level = 0
            title = heading.group(2)
            if title.lower() in _REQUIREMENT_SECTIONS or (
                not level and _REQUIREMENT_ID.search(title)
            ):
                level = depth
        if level or _DEFINITION.match(line):
            kept.append(_normalized(line))
    return "\n".join(line for line in kept if line)


def stable_identity(prepared: PreparedReview) -> str:
    """Digest of what a spec or plan review judged; the review budget is not part of it."""
    from validator.semantic import review_context as context

    texts: dict[str, list[str]] = {}
    roles: dict[str, str] = {}
    for section in prepared.sections:
        texts.setdefault(section.source, []).append(section.text)
        roles.setdefault(section.source, section.role)
    sources = {}
    for source, chunks in sorted(texts.items()):
        text = "".join(chunks)
        lifecycle = context.is_lifecycle_source(source, roles[source], prepared.feature)
        if lifecycle and roles[source] == "spec":
            digest = hashlib.sha256(requirement_projection(text).encode()).hexdigest()
            sources[source] = "requirements:" + digest
        else:
            sources[source] = normative_hash(text, lifecycle_document=lifecycle)
    identity = {
        "feature": prepared.feature,
        "kind": prepared.kind,
        "model": prepared.reviewer_model,
        "versions": [prepared.policy_version, prepared.schema_version, prepared.prompt_version],
        "requirement_scope": prepared.requirement_scope,
        "dependencies": prepared.dependencies,
        "roles": roles,
        "sources": sources,
    }
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


def reviewed_against(
    receipt: ReviewReceipt,
    prepared: PreparedReview,
    accepted: frozenset[str] = frozenset(),
) -> PreparedReview | None:
    """The context a spec or plan receipt is valid against, or None when it is stale.

    ``accepted`` holds context hashes recorded by an open spec revision: such a receipt
    is accepted without comparing its stable identity, but it must still rebuild.
    """
    from validator.semantic.review_receipts import verify_review_receipt

    if verify_review_receipt(receipt, prepared):
        return prepared
    reviewed = receipt.reviewed
    if reviewed is None or not prepared.cacheable or reviewed.context_hash != receipt.context_hash:
        return None
    current = reviewed_snapshot(prepared)
    fields = (
        "feature",
        "kind",
        "reviewer_model",
        "policy_version",
        "schema_version",
        "prompt_version",
    )
    if any(getattr(reviewed, name) != getattr(current, name) for name in fields):
        return None
    if receipt.context_hash not in accepted and stable_identity(reviewed) != stable_identity(
        current
    ):
        return None
    return reviewed if verify_review_receipt(receipt, reviewed) else None
