"""Package exact native reviewer bytes without manufacturing an approval."""

from __future__ import annotations

from pathlib import Path

from .locks import acquire_lock
from .penflow_approval_files import (
    ARCHIVE,
    JsonObject,
    PenflowApprovalError,
    archive_bytes,
    archive_json,
    bounded,
    file_ref,
    load_object,
    read_ref,
)
from .penflow_approval_models import Review, ReviewResult, ReviewSnapshot
from .penflow_review_snapshot import review_requirement_ids, validate_snapshot_inputs


# @spec FR-007: package actual reviewer bytes automatically
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-007
def package_review_result(project_root: Path, snapshot_path: Path, output_path: Path) -> JsonObject:
    """Archive a complete review response and bind it to the reviewed workflow input.

    This transport step may package a blocking review; only the existing approval
    transition can accept a review. No missing reviewer field is synthesized.
    """
    root = project_root.resolve()
    with acquire_lock(root / ".specs"):
        snapshot_ref = file_ref(root, bounded(root, snapshot_path))
        expected_path = str(ARCHIVE / f"snapshot-{snapshot_ref['sha256']}.json")
        if snapshot_ref["path"] != expected_path:
            raise PenflowApprovalError("review_snapshot_not_workflow_archive")
        snapshot = ReviewSnapshot.model_validate(
            load_object(read_ref(root, snapshot_ref))
        ).model_dump(mode="json")
        validate_snapshot_inputs(root, snapshot, snapshot["feature"])
        output_ref = file_ref(root, output_path)
        raw = read_ref(root, output_ref)
        value = load_object(raw)
        if "output" in value:
            raise PenflowApprovalError("review_output_must_be_raw_response")
        review = Review.model_validate({**value, "output": output_ref}).model_dump(mode="json")
        known = review_requirement_ids(root, snapshot)
        blocking = sum(item["severity"] == "BLOCKING" for item in review["findings"])
        if (
            review["input_sha256"] != snapshot_ref["sha256"]
            or review["blocking_count"] != blocking
            or (review["verdict"] == "PASS") != (blocking == 0)
            or any(set(item["requirement_ids"]) - known for item in review["findings"])
        ):
            raise PenflowApprovalError("review_response_identity_or_verdict_mismatch")
        review["output"] = archive_bytes(root, raw, prefix="review-output")
        result = ReviewResult.model_validate(
            {
                "kind": "livespec-penflow-review-result",
                "version": 1,
                "snapshot": snapshot_ref,
                "review": review,
            }
        ).model_dump(mode="json")
        validate_snapshot_inputs(root, snapshot, snapshot["feature"])
        read_ref(root, snapshot_ref)
        if file_ref(root, output_path) != output_ref:
            raise PenflowApprovalError("review_input_changed_during_packaging")
        reference = archive_json(root, result, prefix="review-result")
    return {"result": reference, "verdict": review["verdict"], "certified": False}
