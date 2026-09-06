"""Snapshot the workflow-selected source inputs before real plan review."""

from __future__ import annotations

from pathlib import Path

from .locks import acquire_lock
from .parser import parse_file
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
from .penflow_approval_models import RequirementsBaseline, ReviewSnapshot
from .penflow_contract_validation import validate_review_contract
from .penflow_policy_source import (
    generate_plan_policy_source,
    snapshot_policy_source,
    validate_policy_reference,
)
from .penflow_requirement_projection import (
    project_requirements,
    project_retired_requirements,
    projection_identity,
)
from .penflow_requirement_source import semantic_source_sha256


def source_record(root: Path, path: Path) -> JsonObject:
    """Archive reviewed source bytes and retain its independent semantic identity."""
    reference = file_ref(root, path)
    raw = path.read_bytes()
    if digest(raw) != reference["sha256"]:
        raise PenflowApprovalError("source_changed_during_snapshot")
    record = {
        **reference,
        "semantic_sha256": semantic_source_sha256(path),
        "reviewed_snapshot": archive_bytes(root, raw, prefix="source", suffix=".md"),
    }
    if path.read_bytes() != raw:
        raise PenflowApprovalError("source_changed_during_snapshot")
    return record


def scope_for(root: Path) -> JsonObject:
    """Use the fixed canonical consumer workspace independently of candidate metadata."""
    return {"project_root": str(root.resolve()), "workspace": str(bounded(root, "penflow"))}


def selected_feature(root: Path, feature: str) -> Path:
    """Resolve the exact caller selection without guessing from backlog files."""
    path = bounded(root, Path(".specs/features") / feature)
    if not feature or path.parent != bounded(root, ".specs/features") or not path.is_dir():
        raise PenflowApprovalError("invalid_approved_feature_selection")
    return path


def prior_baseline(root: Path) -> tuple[JsonObject | None, JsonObject | None]:
    """Archive the accepted prior baseline before replacing its current pointer."""
    path = bounded(root, BASELINE)
    if not path.exists():
        if any((root / ARCHIVE).glob("baseline-*.json")):
            raise PenflowApprovalError("accepted_baseline_removed")
        return None, None
    raw = path.read_bytes()
    value = RequirementsBaseline.model_validate(load_object(raw)).model_dump(mode="json")
    return archive_bytes(root, raw, prefix="baseline"), value


def source_changes(
    prior: JsonObject | None, sources: list[JsonObject], projection: JsonObject, contract_sha: str
) -> list[JsonObject]:
    """Describe exact changes from the immutable prior selection and mapping."""
    if prior is None:
        return []
    old_sources = {row["path"]: row for row in prior["sources"]}
    current = {row["path"]: row for row in sources}
    old_ids = {row["id"] for row in prior["projection"]["requirements"]}
    ids = {row["id"] for row in projection["requirements"]}
    old_bindings = {
        f"{row['requirement_id']}:{row['obligation_id']}": row
        for row in prior["projection"]["bindings"]
    }
    new_bindings = {
        f"{row['requirement_id']}:{row['obligation_id']}": row for row in projection["bindings"]
    }
    changed = sorted(
        key
        for key in old_bindings.keys() | new_bindings.keys()
        if old_bindings.get(key) != new_bindings.get(key)
    )
    result = []
    for path in sorted(old_sources.keys() | current.keys()):
        before, after = old_sources.get(path), current.get(path)
        if before != after or changed or prior["contract"]["sha256"] != contract_sha:
            result.append(
                {
                    "source_path": path,
                    "old_sha256": before["sha256"] if before else digest(b""),
                    "new_sha256": after["sha256"] if after else digest(b""),
                    "removed_requirement_ids": sorted(old_ids - ids),
                    "changed_binding_ids": changed,
                }
            )
    return result


def active_features(value: JsonObject) -> list[str]:
    """Return the exhaustive active denominator from governed caller authority."""
    return [name for name in value["selection"] if name not in value["retired_features"]]


def review_requirement_ids(root: Path, snapshot: JsonObject) -> set[str]:
    """Allow findings on current and authenticated prior IDs, not active bindings."""
    known = {item["id"] for item in snapshot["projection"]["requirements"]}
    previous = snapshot["prior_receipt"]
    if previous is not None:
        prior = RequirementsBaseline.model_validate(load_object(read_ref(root, previous)))
        known.update(item.id for item in prior.projection.requirements)
    return known


def validate_selection(snapshot: JsonObject, prior: JsonObject | None) -> None:
    """Require cumulative membership; only the reviewed feature can change disposition."""
    selected = snapshot["selection"]
    retired = snapshot["retired_features"]
    feature = snapshot["feature"]
    expected = sorted(set(prior["selection"] if prior else []) | {feature})
    prior_retired = set(prior["retired_features"] if prior else [])
    if (
        selected != expected
        or retired != sorted(set(retired))
        or not set(retired) <= set(selected)
        or set(retired) - {feature} != prior_retired - {feature}
        or (feature in retired and (prior is None or feature not in prior["selection"]))
        or snapshot["disposition"] != ("active" if active_features(snapshot) else "retired")
    ):
        raise PenflowApprovalError("review_cumulative_selection_mismatch")


def _source_records(
    root: Path, selected: list[str], filename: str, previous: list[JsonObject]
) -> list[JsonObject]:
    prior = {item["path"]: item for item in previous}
    result = []
    for slug in selected:
        path = selected_feature(root, slug) / filename
        item = prior.get(str(path.relative_to(root)))
        if item is not None and semantic_source_sha256(path) == item["semantic_sha256"]:
            # Keep authenticated raw reviewed identity through generated lifecycle edits.
            if digest(read_ref(root, item["reviewed_snapshot"])) != item["sha256"]:
                raise PenflowApprovalError("reviewed_source_identity_mismatch")
            result.append(item)
        else:
            result.append(source_record(root, path))
    return result


def _projection(root: Path, snapshot: JsonObject, contract_raw: bytes) -> JsonObject:
    active = active_features(snapshot)
    if not active:
        return project_retired_requirements()
    paths = {f".specs/features/{name}/spec.md" for name in active}
    records = [row for row in snapshot["inputs"]["sources"] if row["path"] in paths]
    refs = [{"path": row["path"], "sha256": row["sha256"]} for row in records]
    inherited = None
    policy_ref = snapshot["inputs"].get("verification_policy")
    if policy_ref is not None:
        policy = load_object(read_ref(root, policy_ref))
        if policy["inherited_authority"] is not None:
            from .penflow_authority_projection import project_imported_authority

            inherited = project_imported_authority(
                root,
                policy["inherited_authority"],
                bounded(root, snapshot["inputs"]["contract"]["path"]),
            )
    return project_requirements(
        root,
        active,
        refs,
        load_object(contract_raw),
        reviewed_sources=records,
        inherited_projection=inherited,
    )


# @spec FR-007: immutable cumulative inputs before reviewer dispatch
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-007
def create_review_snapshot(project_root: Path, feature_slug: str) -> JsonObject:
    """Snapshot every governed source and plan, adding only the workflow feature."""
    root = project_root.resolve()
    feature = selected_feature(root, feature_slug)
    with acquire_lock(root / ".specs"):
        prior_ref, prior = prior_baseline(root)
        prior_snapshot: JsonObject | None = None
        if prior is not None:
            from .penflow_review_approval import validate_approval_history

            prior_snapshot = validate_approval_history(root, prior)
        selected = sorted(set(prior["selection"] if prior else []) | {feature_slug})
        retired = set(prior["retired_features"] if prior else [])
        if parse_file(feature / "spec.md").metadata.get("visual") is False:
            if prior is None or feature_slug not in prior["selection"]:
                raise PenflowApprovalError("visual_retirement_requires_prior_approval")
            retired.add(feature_slug)
        else:
            retired.discard(feature_slug)
        disposition = "active" if set(selected) - retired else "retired"
        sources = _source_records(root, selected, "spec.md", prior["sources"] if prior else [])
        plans = _source_records(
            root, selected, "plan.md", prior_snapshot["inputs"]["plans"] if prior_snapshot else []
        )
        generate_plan_policy_source(root, plans, sorted(set(selected) - retired))
        contract_path = bounded(root, "penflow/flow-ui-contract/contract.json")
        if disposition == "retired":
            assert prior_snapshot is not None
            contract_raw = read_ref(root, prior_snapshot["inputs"]["contract"])
        else:
            contract_raw = contract_path.read_bytes()
        contract_ref = archive_bytes(root, contract_raw, prefix="contract")
        if disposition == "active":
            validate_review_contract(root, bounded(root, contract_ref["path"]))
        value: JsonObject = {
            "kind": "livespec-penflow-review-snapshot",
            "version": 1,
            "command": "spec-plan",
            "disposition": disposition,
            "retired_features": sorted(retired),
            "feature": feature_slug,
            "scope": scope_for(root),
            "selection": selected,
            "inputs": {
                "sources": sources,
                "plans": plans,
                "contract": contract_ref,
                "verification_policy": snapshot_policy_source(root, load_object(contract_raw)),
                "selection_sha256": digest(json_bytes(selected)),
            },
            "prior_receipt": prior_ref,
        }
        projection = _projection(root, value, contract_raw)
        value["inputs"]["projection_sha256"] = projection_identity(projection)
        value["projection"] = projection
        value["changes"] = source_changes(prior, sources, projection, contract_ref["sha256"])
        snapshot = ReviewSnapshot.model_validate(value).model_dump(mode="json")
        validate_snapshot_inputs(root, snapshot, feature_slug)
        reference = archive_json(root, snapshot, prefix="snapshot")
    return {
        "snapshot": reference,
        "input_sha256": reference["sha256"],
        "feature": feature_slug,
        "selection": selected,
    }


def validate_snapshot_inputs(root: Path, snapshot: JsonObject, feature_slug: str) -> None:
    """Revalidate all reviewed bytes and current semantics before approval or closure."""
    selected_feature(root, feature_slug)
    selected = snapshot["selection"]
    if snapshot["scope"] != scope_for(root) or snapshot["feature"] != feature_slug:
        raise PenflowApprovalError("review_selection_or_scope_mismatch")
    prior_ref = snapshot["prior_receipt"]
    prior = load_object(read_ref(root, prior_ref)) if prior_ref else None
    validate_selection(snapshot, prior)
    inputs = snapshot["inputs"]
    if inputs["selection_sha256"] != digest(json_bytes(selected)):
        raise PenflowApprovalError("review_selection_identity_mismatch")
    expected_paths = [f".specs/features/{name}/spec.md" for name in selected]
    expected_plans = [f".specs/features/{name}/plan.md" for name in selected]
    if [item["path"] for item in inputs["sources"]] != expected_paths or [
        item["path"] for item in inputs["plans"]
    ] != expected_plans:
        raise PenflowApprovalError("review_source_membership_mismatch")
    for item in [*inputs["sources"], *inputs["plans"]]:
        raw = read_ref(root, item["reviewed_snapshot"])
        archived = bounded(root, item["reviewed_snapshot"]["path"])
        if (
            digest(raw) != item["sha256"]
            or semantic_source_sha256(archived) != item["semantic_sha256"]
        ):
            raise PenflowApprovalError("reviewed_source_identity_mismatch")
        if semantic_source_sha256(bounded(root, item["path"])) != item["semantic_sha256"]:
            raise PenflowApprovalError("approved_source_semantics_changed")
    for name in snapshot["retired_features"]:
        if (
            parse_file(bounded(root, f".specs/features/{name}/spec.md")).metadata.get("visual")
            is not False
        ):
            raise PenflowApprovalError("retirement_not_explicitly_approved")
    contract_raw = read_ref(root, inputs["contract"])
    policy_ref = inputs.get("verification_policy")
    if policy_ref is not None:
        policy = validate_policy_reference(
            root,
            policy_ref,
            load_object(contract_raw),
            current=True,
            contract_path=bounded(root, inputs["contract"]["path"]),
            plans=inputs["plans"],
            active=sorted(set(selected) - set(snapshot["retired_features"])),
        )
        if prior is not None:
            from .penflow_review_approval import validate_approval_history

            prior_snapshot = validate_approval_history(root, prior)
            prior_policy_ref = prior_snapshot["inputs"].get("verification_policy")
            if prior_policy_ref is not None:
                previous_policy = load_object(read_ref(root, prior_policy_ref))
                inherited = previous_policy["inherited_authority"]
                if inherited is not None and policy["inherited_authority"] != inherited:
                    raise PenflowApprovalError("inherited_authority_cannot_be_removed_or_replaced")
    if (
        snapshot["disposition"] == "active"
        and bounded(root, "penflow/flow-ui-contract/contract.json").read_bytes() != contract_raw
    ):
        raise PenflowApprovalError("reviewed_contract_changed")
    projection = _projection(root, snapshot, contract_raw)
    if (
        projection != snapshot["projection"]
        or projection_identity(projection) != inputs["projection_sha256"]
    ):
        raise PenflowApprovalError("reviewed_projection_changed")
