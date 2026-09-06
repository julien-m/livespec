"""Generate a reviewed denominator from explicit source selection and canonical mappings."""

from __future__ import annotations

from pathlib import Path

from .penflow_approval_files import JsonObject, PenflowApprovalError, bounded, digest, json_bytes
from .penflow_approval_models import ExpectedOutcome, Projection, RetiredProjection
from .penflow_requirement_source import extract_requirement_definitions


# @spec FR-007: actual source definitions and reviewed outcome mapping
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-007
def project_requirements(
    root: Path,
    selection: list[str],
    source_refs: list[JsonObject],
    contract: JsonObject,
    *,
    reviewed_sources: list[JsonObject] | None = None,
    inherited_projection: JsonObject | None = None,
) -> JsonObject:
    """Project actual selected definitions; never infer categories from prose.

    Canonical bindings select obligations, not source membership. Missing
    mappings stay explicitly uncovered. Unknown or duplicate references fail.
    """
    requirements: list[JsonObject] = []
    reviewed = {row["path"]: row for row in reviewed_sources or []}
    for feature in selection:
        path = root / ".specs/features" / feature / "spec.md"
        record = reviewed.get(str(path.relative_to(root)))
        if record is not None:
            path = bounded(root, record["reviewed_snapshot"]["path"])
        for item in extract_requirement_definitions(path, feature):
            requirements.append(
                {
                    "id": item.id,
                    "source_pointer": item.source_pointer,
                    "text_sha256": item.text_sha256,
                }
            )
    if inherited_projection is not None:
        requirements.extend(inherited_projection["requirements"])
        source_refs = [*source_refs, *inherited_projection["sources"]]
    ids = {row["id"] for row in requirements}
    if len(ids) != len(requirements) or not ids:
        raise PenflowApprovalError("invalid_requirement_denominator")
    declared = contract.get("requirements")
    if not isinstance(declared, dict) or declared.get("source_kind") != "livespec-fr-ac-v1":
        raise PenflowApprovalError("canonical_livespec_requirements_required")
    if declared.get("source_refs") != source_refs:
        raise PenflowApprovalError("canonical_source_selection_mismatch")
    raw_bindings = declared.get("bindings")
    raw_outcomes = contract.get("outcome_expectations")
    if not isinstance(raw_bindings, list) or not isinstance(raw_outcomes, list):
        raise PenflowApprovalError("canonical_bindings_and_outcomes_required")
    outcomes: dict[str, JsonObject] = {}
    for raw in raw_outcomes:
        outcome = ExpectedOutcome.model_validate(raw).model_dump(mode="json")
        identity = outcome["obligation_id"]
        if identity in outcomes:
            raise PenflowApprovalError(f"duplicate_outcome: {identity}")
        outcomes[identity] = outcome
    bindings: list[JsonObject] = []
    seen: set[tuple[str, str]] = set()
    for raw in raw_bindings:
        if not isinstance(raw, dict) or set(raw) != {"requirement_id", "obligation_id"}:
            raise PenflowApprovalError("invalid_canonical_requirement_binding")
        requirement, obligation = raw["requirement_id"], raw["obligation_id"]
        if not isinstance(requirement, str) or not isinstance(obligation, str):
            raise PenflowApprovalError("invalid_binding_identity")
        if (
            requirement not in ids
            or obligation not in outcomes
            or (requirement, obligation) in seen
        ):
            raise PenflowApprovalError("unknown_or_duplicate_requirement_binding")
        seen.add((requirement, obligation))
        expected = outcomes[obligation]
        bindings.append(
            {
                "requirement_id": requirement,
                "obligation_id": obligation,
                "category": expected["category"],
                "expected": expected,
            }
        )
    result = {
        "source_kind": "livespec-fr-ac-v1",
        "sources": source_refs,
        "requirements": requirements,
        "bindings": bindings,
        "uncovered": sorted(ids - {item["requirement_id"] for item in bindings}),
    }
    return Projection.model_validate(result).model_dump(mode="json")


def projection_identity(projection: JsonObject) -> str:
    """Bind requirement membership, categories and predicates to reviewed bytes."""
    return digest(json_bytes(projection))


def project_retired_requirements() -> JsonObject:
    """Record a reviewed retirement without pretending old UI bindings remain active."""
    return RetiredProjection.model_validate(
        {
            "source_kind": "livespec-fr-ac-v1",
            "sources": [],
            "requirements": [],
            "bindings": [],
            "uncovered": [],
        }
    ).model_dump(mode="json")
