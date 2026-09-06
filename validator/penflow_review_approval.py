"""Accept real bound review results and revalidate approved source authority."""

from __future__ import annotations

from pathlib import Path

from .locks import write_with_hash_check
from .penflow_approval_files import (
    ARCHIVE,
    BASELINE,
    JsonObject,
    PenflowApprovalError,
    archive_bytes,
    archive_json,
    bounded,
    digest,
    file_ref,
    json_bytes,
    load_object,
    read_ref,
)
from .penflow_approval_models import (
    RequirementsBaseline,
    ReviewApproval,
    ReviewResult,
    ReviewSnapshot,
)
from .penflow_review_snapshot import (
    active_features,
    review_requirement_ids,
    source_changes,
    validate_selection,
    validate_snapshot_inputs,
)


def validate_review_output(root: Path, review: JsonObject) -> None:
    """Check the actual reviewer output, rather than trusting copied PASS fields."""
    output = load_object(read_ref(root, review["output"]))
    expected = {key: value for key, value in review.items() if key != "output"}
    if (
        json_bytes(output) != json_bytes(expected)
        or review["verdict"] != "PASS"
        or review["blocking_count"] != 0
    ):
        raise PenflowApprovalError("review_output_not_approved")
    rows = output.get("findings")
    if not isinstance(rows, list) or any(
        not isinstance(row, dict) or row.get("severity") == "BLOCKING" for row in rows
    ):
        raise PenflowApprovalError("review_blocking_findings")


def validate_approval_history(root: Path, baseline: JsonObject) -> JsonObject:
    """Verify immutable prior history without comparing old bytes to current source."""
    current = baseline
    seen: set[str] = set()
    verified_sources: set[tuple[str, str, str]] = set()
    latest_snapshot: JsonObject | None = None
    while True:
        current = RequirementsBaseline.model_validate(current).model_dump(mode="json")
        refs = current["approval_receipts"]
        if len(refs) != 1:
            raise PenflowApprovalError("unsupported_approval_selection")
        approval = ReviewApproval.model_validate(load_object(read_ref(root, refs[0]))).model_dump(
            mode="json"
        )
        review = approval["review"]
        validate_review_output(root, review)
        snapshot_ref = approval["snapshot"]
        if snapshot_ref["sha256"] != review["input_sha256"]:
            raise PenflowApprovalError("approval_review_input_mismatch")
        snapshot = ReviewSnapshot.model_validate(
            load_object(read_ref(root, snapshot_ref))
        ).model_dump(mode="json")
        expected_contract = (
            snapshot["inputs"]["contract"]
            if current["disposition"] == "retired"
            else {
                "path": "penflow/flow-ui-contract/contract.json",
                "sha256": snapshot["inputs"]["contract"]["sha256"],
            }
        )
        if (
            current["contract"] != expected_contract
            or approval["disposition"] != current["disposition"]
            or approval["scope"] != current["scope"]
            or approval["selection"] != current["selection"]
            or approval["feature"] not in current["selection"]
            or approval["retired_features"] != current["retired_features"]
            or approval["inputs"]["sources"] != current["sources"]
            or approval["inputs"]["contract"]["sha256"] != current["contract"]["sha256"]
            or approval["prior_receipt"] != current["previous"]
            or snapshot["projection"] != current["projection"]
            or any(
                approval[key] != snapshot[key]
                for key in (
                    "scope",
                    "selection",
                    "feature",
                    "inputs",
                    "prior_receipt",
                    "changes",
                    "disposition",
                    "retired_features",
                )
            )
        ):
            raise PenflowApprovalError("approval_baseline_identity_mismatch")
        for source in [*current["sources"], *approval["inputs"]["plans"]]:
            reference = source["reviewed_snapshot"]
            identity = (reference["path"], reference["sha256"], source["sha256"])
            if identity not in verified_sources:
                if digest(read_ref(root, reference)) != source["sha256"]:
                    raise PenflowApprovalError("historical_source_snapshot_mismatch")
                # Only content-addressed source archives can be reused during this
                # traversal. Every new invocation re-reads them; current files never cache.
                if reference["path"] == str(ARCHIVE / f"source-{reference['sha256']}.md"):
                    verified_sources.add(identity)
        read_ref(root, approval["inputs"]["contract"])
        policy_ref = approval["inputs"].get("verification_policy")
        if policy_ref is not None:
            from .penflow_approval_models import AuthorityImport, PolicySource

            policy = PolicySource.model_validate(load_object(read_ref(root, policy_ref)))
            read_ref(root, policy.workflow.model_dump(mode="json"))
            if policy.inherited_authority is not None:
                packet = AuthorityImport.model_validate(
                    load_object(read_ref(root, policy.inherited_authority.model_dump(mode="json")))
                )
                for item in packet.files:
                    read_ref(root, {"path": item.path, "sha256": item.sha256})
        if latest_snapshot is None:
            latest_snapshot = snapshot
        previous = current["previous"]
        if previous is None:
            validate_selection(snapshot, None)
            if snapshot["changes"]:
                raise PenflowApprovalError("initial_approval_has_prior_changes")
            break
        if previous["sha256"] in seen:
            raise PenflowApprovalError("approval_history_cycle")
        seen.add(previous["sha256"])
        prior = RequirementsBaseline.model_validate(
            load_object(read_ref(root, previous))
        ).model_dump(mode="json")
        validate_selection(snapshot, prior)
        changes = source_changes(
            prior, current["sources"], current["projection"], current["contract"]["sha256"]
        )
        if changes != approval["changes"]:
            raise PenflowApprovalError("approved_source_delta_mismatch")
        current = prior
    assert latest_snapshot is not None
    return latest_snapshot


# @spec FR-007: approve real review before Plan Review Done
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-007
def approve_review_result(project_root: Path, feature_slug: str, result_path: Path) -> JsonObject:
    """Publish a valid baseline before Done, while the caller holds the project lock.

    Atomic per-file writes and immutable archives allow retry after interruption.
    The pipeline must write its completion only after this function succeeds.
    """
    root = project_root.resolve()
    result = ReviewResult.model_validate(
        load_object(bounded(root, result_path).read_bytes())
    ).model_dump(mode="json")
    if result["snapshot"]["path"] != str(ARCHIVE / f"snapshot-{result['snapshot']['sha256']}.json"):
        raise PenflowApprovalError("review_snapshot_not_workflow_archive")
    snapshot = ReviewSnapshot.model_validate(
        load_object(read_ref(root, result["snapshot"]))
    ).model_dump(mode="json")
    review = result["review"]
    if review["input_sha256"] != result["snapshot"]["sha256"]:
        raise PenflowApprovalError("review_input_identity_mismatch")
    validate_review_output(root, review)
    validate_snapshot_inputs(root, snapshot, feature_slug)
    known = review_requirement_ids(root, snapshot)
    if any(set(item["requirement_ids"]) - known for item in review["findings"]):
        raise PenflowApprovalError("review_findings_unknown_requirements")
    immutable_review = {
        **review,
        "output": archive_bytes(root, read_ref(root, review["output"]), prefix="review-output"),
    }
    approval = ReviewApproval.model_validate(
        {
            **{key: value for key, value in snapshot.items() if key != "projection"},
            "kind": "livespec-penflow-review-approval",
            "review": immutable_review,
            "snapshot": result["snapshot"],
        }
    ).model_dump(mode="json")
    approval_ref = archive_json(root, approval, prefix="approval")
    baseline = RequirementsBaseline.model_validate(
        {
            "kind": "livespec-penflow-requirements-baseline",
            "version": 1,
            "disposition": snapshot["disposition"],
            "scope": snapshot["scope"],
            "selection": snapshot["selection"],
            "retired_features": snapshot["retired_features"],
            "approval_receipts": [approval_ref],
            "sources": snapshot["inputs"]["sources"],
            "contract": (
                snapshot["inputs"]["contract"]
                if snapshot["disposition"] == "retired"
                else file_ref(root, bounded(root, "penflow/flow-ui-contract/contract.json"))
            ),
            "projection": snapshot["projection"],
            "previous": snapshot["prior_receipt"],
        }
    ).model_dump(mode="json")
    validate_approval_history(root, baseline)
    baseline_path = bounded(root, BASELINE)
    if baseline_path.exists():
        existing = load_object(baseline_path.read_bytes())
        if existing == baseline:
            return baseline
        if snapshot["prior_receipt"] is None or baseline_path.read_bytes() != read_ref(
            root, snapshot["prior_receipt"]
        ):
            raise PenflowApprovalError("approval_prior_baseline_changed")
    elif snapshot["prior_receipt"] is not None:
        raise PenflowApprovalError("approved_prior_baseline_removed")
    else:
        expected_path = ARCHIVE / f"baseline-{digest(json_bytes(baseline))}.json"
        if any(
            path.relative_to(root) != expected_path
            for path in (root / ARCHIVE).glob("baseline-*.json")
        ):
            raise PenflowApprovalError("accepted_baseline_removed")
    archive_json(root, baseline, prefix="baseline")
    # Recheck current inputs immediately before publishing authority.
    validate_snapshot_inputs(root, snapshot, feature_slug)
    write_with_hash_check(baseline_path, json_bytes(baseline).decode())
    return baseline


def require_approved_requirements(
    project_root: Path, feature_slug: str | None, *, disposition: str = "active"
) -> None:
    """Require the caller's exact currently approved source selection before C51."""
    if not feature_slug:
        raise PenflowApprovalError("approved_feature_selection_required")
    root = project_root.resolve()
    baseline = RequirementsBaseline.model_validate(
        load_object(bounded(root, BASELINE).read_bytes())
    ).model_dump(mode="json")
    snapshot = validate_approval_history(root, baseline)
    if snapshot["inputs"].get("verification_policy") is None:
        raise PenflowApprovalError("approved_verification_policy_required")
    if feature_slug not in baseline["selection"]:
        raise PenflowApprovalError("review_selection_or_scope_mismatch")
    actual_disposition = "retired" if feature_slug in baseline["retired_features"] else "active"
    if actual_disposition != disposition:
        raise PenflowApprovalError("approved_visual_disposition_mismatch")
    validate_snapshot_inputs(root, snapshot, snapshot["feature"])
    # The latest cumulative review covers all active sources, not just its trigger.
    from .pipeline import _parse_pipeline

    required = set(active_features(baseline)) | {feature_slug}
    for name in sorted(required):
        pipeline = bounded(root, f".specs/features/{name}/pipeline.md")
        if _parse_pipeline(pipeline.read_text()).get("plan-review") != "Done":
            raise PenflowApprovalError("plan_review_not_completed")


def has_approved_feature_history(project_root: Path, feature_slug: str) -> bool:
    """Detect accepted feature authority even if its current pointer was deleted."""
    root = project_root.resolve()
    candidates = [root / BASELINE, *(root / ARCHIVE).glob("baseline-*.json")]
    for path in candidates:
        if path.exists():
            baseline = RequirementsBaseline.model_validate(
                load_object(path.read_bytes())
            ).model_dump(mode="json")
            if feature_slug in baseline["selection"]:
                return True
    return False
