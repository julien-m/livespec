"""Persist accepted clarification decisions without changing requirement IDs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import replace
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from validator.clarify_gate import ClarifyOpportunity

_MARKER = re.compile(r"<!-- livespec-clarification:(.+?) -->")
_REQUIREMENT = re.compile(r"\b(?:FR|AC|SC)-\d+\b")


class RecordedDecision(BaseModel):
    """A generated annotation bound to the exact original ambiguity excerpt."""

    model_config = ConfigDict(extra="forbid", strict=True)
    requirement_id: str
    decision_key: str
    evidence_hash: str
    answer: str


def apply_recorded_decisions(
    spec_path: Path, items: list[ClarifyOpportunity]
) -> list[ClarifyOpportunity]:
    """Reuse accepted decisions only while the cited ambiguity excerpt remains identical."""
    decisions: dict[tuple[str, str, str], RecordedDecision] = {}
    for raw in _MARKER.findall(spec_path.read_text(encoding="utf-8")):
        try:
            decision = RecordedDecision.model_validate_json(raw)
        except ValidationError:
            continue  # Invalid annotations remain unresolved; they never satisfy the gate.
        decisions[(decision.requirement_id, decision.decision_key, decision.evidence_hash)] = (
            decision
        )
    result = []
    for item in items:
        key = (
            item.requirement_id,
            item.decision_key,
            hashlib.sha256(item.evidence_text.encode()).hexdigest(),
        )
        recorded = decisions.get(key)
        result.append(
            replace(
                item,
                resolution=recorded.answer,
                resolution_provenance=(f"{spec_path}#clarifications",),
            )
            if recorded
            else item
        )
    return result


# @spec FR-008: Accepted source decisions
# — .specs/features/078-requirement-evidence-integrity/spec.md#fr-008


def persist_clarification_decision(
    spec_path: Path, opportunity: ClarifyOpportunity, answer: str
) -> str:
    """Atomically append an explicitly accepted answer; return the new source hash.

    Caller owns obtaining the accepted answer. A stale question or new requirement ID is rejected.
    """
    if spec_path.is_symlink():
        raise ValueError("clarification_source_symlink")
    original = spec_path.read_bytes()
    text = original.decode("utf-8")
    if hashlib.sha256(original).hexdigest() != opportunity.source_hash:
        raise ValueError("stale_clarification_source")
    if not answer.strip() or not opportunity.decision_key or opportunity.evidence_text not in text:
        raise ValueError("missing_accepted_decision_or_source")
    if set(_REQUIREMENT.findall(answer)) - set(_REQUIREMENT.findall(text)):
        raise ValueError("decision_would_introduce_requirement_ids")
    decision = RecordedDecision(
        requirement_id=opportunity.requirement_id,
        decision_key=opportunity.decision_key,
        evidence_hash=hashlib.sha256(opportunity.evidence_text.encode()).hexdigest(),
        answer=answer.strip(),
    )
    # Existing Clarifications remains the only user-facing decision ledger.
    annotation = json.dumps(decision.model_dump(), ensure_ascii=False).replace("-->", "--\\u003e")
    entry = (
        f"\n- Decision `{opportunity.requirement_id}` / `{opportunity.decision_key}`: "
        f"{answer.strip()}\n<!-- livespec-clarification:{annotation} -->\n"
    )
    heading = re.search(r"^## Clarifications\s*$", text, re.MULTILINE)
    if heading:
        following = re.search(r"^## ", text[heading.end() :], re.MULTILINE)
        offset = heading.end() + following.start() if following else len(text)
        updated = text[:offset].rstrip() + "\n" + entry + "\n" + text[offset:]
    else:
        updated = text.rstrip() + "\n\n## Clarifications\n" + entry
    _replace_unchanged(spec_path, original, updated.encode())
    return hashlib.sha256(updated.encode()).hexdigest()


def _replace_unchanged(path: Path, original: bytes, updated: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=".clarification-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        if path.read_bytes() != original:
            raise ValueError("clarification_source_changed_during_write")
        os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
