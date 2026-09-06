"""Ask the installed Penflow CLI to project authenticated imported product authority."""

from pathlib import Path

from .penflow_approval_files import JsonObject, PenflowApprovalError, bounded, load_object, read_ref
from .penflow_approval_models import AuthorityImport, Projection, VerificationPolicy

# @spec FR-008: Delegate the inherited product denominator to Penflow
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-008


def project_imported_authority(
    root: Path, reference: JsonObject, contract_path: Path | None = None
) -> JsonObject:
    """Revalidate local imported bytes and delegate product obligations to Penflow.

    Args:
        root: Current consumer boundary; no historical path is opened.
        reference: Immutable import packet selected by the approved workflow.
        contract_path: Current or archived C20 whose explicit mappings are evaluated.

    Returns:
        Producer-validated projection and inherited procedure decisions.
    """
    from .penflow_authority_import import authority_command

    root = root.resolve()
    packet = AuthorityImport.model_validate(load_object(read_ref(root, reference))).model_dump(
        mode="json"
    )
    contract_path = bounded(root, contract_path or "penflow/flow-ui-contract/contract.json")
    references = [
        reference,
        packet["report"],
        *[{"path": row["path"], "sha256": row["sha256"]} for row in packet["files"]],
    ]
    before = [(str(bounded(root, row["path"])), read_ref(root, row)) for row in references]
    contract_raw = contract_path.read_bytes()
    result = authority_command(
        "project",
        [str(bounded(root, reference["path"])), "--contract", str(contract_path)],
        project_root=root,
    )
    if set(result) != {
        "sources",
        "requirements",
        "bindings",
        "uncovered",
        "product",
        "verification_policy",
    }:
        raise PenflowApprovalError("imported_projection_response_invalid")
    Projection.model_validate(
        {
            "source_kind": "brainstorm-product-v1",
            **{key: result[key] for key in ("sources", "requirements", "bindings", "uncovered")},
        }
    )
    VerificationPolicy.model_validate(result["verification_policy"])
    if result["uncovered"]:
        raise PenflowApprovalError("imported_requirements_uncovered")
    after = [(str(bounded(root, row["path"])), read_ref(root, row)) for row in references]
    if before != after or contract_path.read_bytes() != contract_raw:
        raise PenflowApprovalError("imported_authority_changed_during_projection")
    return result
