"""Archive workflow-owned verification decisions before cumulative plan review."""

from __future__ import annotations

from pathlib import Path

import yaml

from .locks import acquire_lock, write_with_hash_check
from .penflow_approval_files import (
    ARCHIVE,
    JsonObject,
    PenflowApprovalError,
    archive_bytes,
    archive_json,
    bounded,
    file_ref,
    json_bytes,
    load_object,
    read_ref,
)
from .penflow_approval_models import File, PolicySource, VerificationPolicy

POLICY_SOURCE = Path(".specs/penflow-verification-policy.json")
AUTHORITY_POINTER = Path(".specs/penflow-brainstorm-authority.json")

# @spec FR-008: Preserve workflow-owned imported authority
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-008


def _workflow_metadata(raw: bytes) -> JsonObject:
    """Read unambiguous frontmatter, excluding Markdown examples from authority."""
    text = raw.decode("utf-8")
    lines = text.splitlines()

    def boundary(line: str) -> bool:
        value = line.strip()
        return len(value) >= 3 and set(value) == {"-"}

    if not lines or not boundary(lines[0]):
        return {}
    end = next((index for index in range(1, len(lines)) if boundary(lines[index])), None)
    if end is None:
        raise PenflowApprovalError("workflow_policy_frontmatter_unclosed")

    class UniqueLoader(yaml.SafeLoader):
        """Reject duplicate metadata keys instead of silently selecting a policy."""

    def unique_mapping(loader: UniqueLoader, node: yaml.MappingNode) -> JsonObject:
        result: JsonObject = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node)
            if not isinstance(key, str) or key in result:
                raise PenflowApprovalError("workflow_policy_duplicate_or_invalid_key")
            result[key] = loader.construct_object(value_node)
        return result

    UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)
    try:
        metadata = yaml.load("\n".join(lines[1:end]), Loader=UniqueLoader)
    except yaml.YAMLError as exc:
        raise PenflowApprovalError("workflow_policy_metadata_invalid") from exc
    if not isinstance(metadata, dict):
        raise PenflowApprovalError("workflow_policy_metadata_invalid")
    return metadata


def workflow_decisions(raw: bytes, *, inherited: bool) -> JsonObject:
    """Read one explicit closed workflow mode; artifact absence never selects policy."""
    metadata = _workflow_metadata(raw)
    modes = metadata.get("penflow_verification_policy")
    if not isinstance(modes, dict) or not modes or set(modes) - {"livespec", "brainstorm_handoff"}:
        raise PenflowApprovalError("workflow_policy_modes_required")
    for value in modes.values():
        VerificationPolicy.model_validate(value)
    mode = "brainstorm_handoff" if inherited else "livespec"
    if mode not in modes:
        raise PenflowApprovalError(f"workflow_policy_mode_missing: {mode}")
    return VerificationPolicy.model_validate(modes[mode]).model_dump(mode="json")


def has_workflow_policy(raw: bytes) -> bool:
    """Detect only an actual frontmatter policy declaration, not a body example."""
    return "penflow_verification_policy" in _workflow_metadata(raw)


def _plan_decisions(contents: list[bytes], *, inherited: bool) -> JsonObject | None:
    present = [has_workflow_policy(raw) for raw in contents]
    if not any(present):
        return None
    if not all(present):
        raise PenflowApprovalError("verification_policy_required_in_every_active_plan")
    decisions = [workflow_decisions(raw, inherited=inherited) for raw in contents]
    combined: JsonObject = {"version": 1}
    for key in decisions[0]:
        if key != "version":
            combined[key] = (
                "required"
                if any(value[key] == "required" for value in decisions)
                else "not_applicable"
            )
    return combined


def generate_plan_policy_source(root: Path, plans: list[JsonObject], active: list[str]) -> None:
    """Generate the standard workflow policy from every active reviewed plan.

    The caller holds the project lock. A dedicated existing workflow is retained
    only when none of the plans declares policy; mixed declarations fail closed.
    """
    records = [row for row in plans if Path(row["path"]).parent.name in active]
    contents = [read_ref(root, row["reviewed_snapshot"]) for row in records]
    inherited = inherited_reference(root)
    combined = _plan_decisions(contents, inherited=inherited is not None)
    if combined is None:
        return
    mode = "brainstorm_handoff" if inherited is not None else "livespec"
    # Preserve every complete plan below its identity; the reviewer and core see
    # the same exhaustive active union rather than only the most recent plan.
    text = (
        "---\n"
        + yaml.safe_dump({"penflow_verification_policy": {mode: combined}}, sort_keys=True)
        + "---\n\n# Active production plans\n"
    )
    for record, raw in zip(records, contents, strict=True):
        text += f"\n## {record['path']} ({record['sha256']})\n\n" + raw.decode("utf-8") + "\n"
    workflow = archive_bytes(root, text.encode(), prefix="workflow", suffix=".md")
    if inherited is not None:
        from .penflow_authority_projection import project_imported_authority

        projection = project_imported_authority(root, inherited)
        for key, value in projection["verification_policy"].items():
            if key != "version" and value == "required":
                combined[key] = "required"
    source = PolicySource.model_validate(
        {
            "kind": "penflow-verification-policy-source",
            "version": 1,
            "workflow": workflow,
            "decisions": combined,
            "inherited_authority": inherited,
        }
    ).model_dump(mode="json")
    archive_json(root, source, prefix="verification-policy")
    write_with_hash_check(bounded(root, POLICY_SOURCE), json_bytes(source).decode())


def inherited_reference(root: Path) -> JsonObject | None:
    """Resolve the workflow import pointer to its immutable local authority packet."""
    path = bounded(root, AUTHORITY_POINTER)
    if not path.exists():
        if any((root / ARCHIVE).glob("authority-*.json")):
            raise PenflowApprovalError("imported_authority_pointer_removed")
        return None
    reference = File.model_validate(load_object(path.read_bytes())).model_dump(mode="json")
    read_ref(root, reference)
    return reference


def generate_policy_source(root: Path, workflow_path: Path) -> JsonObject:
    """Publish decisions read from the actual workflow, preserving its reviewed bytes.

    Args:
        root: Consumer project whose existing lock owns publication.
        workflow_path: Actual producing workflow; it may be installed outside the project.

    Returns:
        Relative reference to the generated policy source. No C20 content is changed.
    """
    root = root.resolve()
    original_path = workflow_path.absolute()
    workflow = original_path.resolve(strict=True)
    raw = workflow.read_bytes()
    with acquire_lock(root / ".specs"):
        inherited = inherited_reference(root)
        decisions = workflow_decisions(raw, inherited=inherited is not None)
        if inherited is not None:
            from .penflow_authority_projection import project_imported_authority

            projection = project_imported_authority(root, inherited)
            # An inherited required procedure cannot be disabled by the current mode.
            for key, value in projection["verification_policy"].items():
                if key != "version" and value == "required":
                    decisions[key] = "required"
        workflow_ref = archive_bytes(root, raw, prefix="workflow", suffix=".md")
        source = PolicySource.model_validate(
            {
                "kind": "penflow-verification-policy-source",
                "version": 1,
                "workflow": workflow_ref,
                "decisions": decisions,
                "inherited_authority": inherited,
            }
        ).model_dump(mode="json")
        if original_path.resolve(strict=True) != workflow or workflow.read_bytes() != raw:
            raise PenflowApprovalError("workflow_changed_during_policy_generation")
        if inherited_reference(root) != inherited:
            raise PenflowApprovalError("authority_changed_during_policy_generation")
        archive_json(root, source, prefix="verification-policy")
        path = bounded(root, POLICY_SOURCE)
        write_with_hash_check(path, json_bytes(source).decode())
        return file_ref(root, path)


def validate_policy_reference(
    root: Path,
    reference: JsonObject,
    contract: JsonObject,
    *,
    current: bool = False,
    contract_path: Path | None = None,
    plans: list[JsonObject] | None = None,
    active: list[str] | None = None,
) -> JsonObject:
    """Authenticate archived decisions and their actual workflow without changing policy."""
    source = PolicySource.model_validate(load_object(read_ref(root, reference))).model_dump(
        mode="json"
    )
    raw = read_ref(root, source["workflow"])
    decisions = workflow_decisions(raw, inherited=source["inherited_authority"] is not None)
    if plans is not None and active is not None:
        contents = [
            read_ref(root, row["reviewed_snapshot"])
            for row in plans
            if Path(row["path"]).parent.name in active
        ]
        plan_decisions = _plan_decisions(
            contents, inherited=source["inherited_authority"] is not None
        )
        if plan_decisions is not None and decisions != plan_decisions:
            raise PenflowApprovalError("active_plan_verification_policy_mismatch")
    if source["inherited_authority"] is not None:
        from .penflow_authority_projection import project_imported_authority

        inherited = project_imported_authority(root, source["inherited_authority"], contract_path)
        for key, value in inherited["verification_policy"].items():
            if key != "version" and value == "required":
                decisions[key] = "required"
    if source["decisions"] != decisions or contract.get("verification_policy") != decisions:
        raise PenflowApprovalError("reviewed_verification_policy_mismatch")
    if current:
        if bounded(root, POLICY_SOURCE).read_bytes() != read_ref(root, reference):
            raise PenflowApprovalError("verification_policy_source_changed")
        if inherited_reference(root) != source["inherited_authority"]:
            raise PenflowApprovalError("inherited_authority_omitted_or_changed")
    return source


def snapshot_policy_source(root: Path, contract: JsonObject) -> JsonObject:
    """Require and archive the explicit workflow input for every new review snapshot."""
    path = bounded(root, POLICY_SOURCE)
    if not path.is_file():
        raise PenflowApprovalError(
            "verification_policy_source_required: generate from the producing workflow"
        )
    reference = file_ref(root, path)
    validate_policy_reference(root, reference, contract, current=True)
    return archive_bytes(root, read_ref(root, reference), prefix="verification-policy")
