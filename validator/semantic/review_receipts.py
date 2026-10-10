"""Review transport, exact reusable receipts and independent revalidation (078 FR-004)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from validator.semantic.review_context import PreparedReview
from validator.semantic.review_contract import REVIEW_SCHEMA, ReviewReceipt, validate_review_result
from validator.semantic.review_synthesis_transport import synthesis_prompt as synthesis_prompt


def save_review_receipt(path: Path, receipt: ReviewReceipt) -> Path:
    """Atomically publish generated evidence; never follow a destination symlink."""
    if path.is_symlink():
        raise ValueError("review_receipt_symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".review-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(receipt.model_dump_json(indent=2))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return path


def load_review_receipt(path: Path) -> ReviewReceipt:
    """Parse strict receipt bytes; a missing, malformed or linked file raises."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
        return ReviewReceipt.model_validate_json(stream.read())


def verify_review_receipt(receipt_or_path: ReviewReceipt | Path, prepared: PreparedReview) -> bool:
    """Revalidate raw evidence and exact identities rather than submitted booleans."""
    try:
        receipt = (
            load_review_receipt(receipt_or_path)
            if isinstance(receipt_or_path, Path)
            else receipt_or_path
        )
    except (OSError, ValueError, ValidationError):
        return False
    if not prepared.cacheable or receipt.context_hash != prepared.context_hash:
        return False
    rebuilt = validate_review_result(prepared, receipt.raw_results, receipt.synthesis)
    # Original raw hashes remain provenance when approved lifecycle metadata changes.
    return rebuilt.complete and receipt.model_dump(exclude={"source_hashes"}) == rebuilt.model_dump(
        exclude={"source_hashes"}
    )


def run_prepared_review(
    prepared: PreparedReview, *, cache_path: Path | None = None, model: str | None = None
) -> ReviewReceipt:
    """Run bounded submissions; exact complete cache hits perform no provider calls."""
    from validator.llm_provider import call_llm

    if model and prepared.cacheable and model != prepared.reviewer_model:
        raise ValueError("reviewer_model_mismatch")
    if cache_path and cache_path.exists():
        try:
            cached = load_review_receipt(cache_path)
        except (OSError, ValueError, ValidationError):
            cached = None
        if cached is not None and verify_review_receipt(cached, prepared):
            return cached
    actual_model = model or (prepared.reviewer_model if prepared.cacheable else None)
    raw_results: list[str] = []
    synthesis = None
    if prepared.complete:
        for batch in prepared.batches:
            raw_results.append(
                call_llm(batch.prompt, json_schema=REVIEW_SCHEMA, model=actual_model)
            )
        if len(prepared.batches) > 1:
            prompt = synthesis_prompt(prepared, raw_results)
            if len(prompt) <= prepared.max_chars:
                synthesis = call_llm(prompt, json_schema=REVIEW_SCHEMA, model=actual_model)
    receipt = validate_review_result(prepared, raw_results, synthesis)
    if cache_path:
        save_review_receipt(cache_path, receipt)
    return receipt


def legacy_display_fields(receipt: ReviewReceipt) -> tuple[list[dict[str, Any]], int]:
    """Keep old display-only responses readable without granting current completeness."""
    if receipt.complete:
        return [finding.model_dump() for finding in receipt.findings], receipt.confidence
    findings: list[dict[str, Any]] = []
    confidence = receipt.confidence
    for raw in receipt.raw_results:
        # Legacy wrappers historically raise JSONDecodeError; preserve that boundary.
        data = json.loads(raw)
        if not isinstance(data, dict):
            continue
        for finding in data.get("findings", []):
            if isinstance(finding, dict):
                findings.append(finding)
        if isinstance(data.get("confidence"), int):
            confidence = data["confidence"]
    return findings, confidence
