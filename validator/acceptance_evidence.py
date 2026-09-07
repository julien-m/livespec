"""Policy2 acceptance conjunction at proof, archive and archive-read boundaries."""

# @spec(FR-009)
# @spec(FR-016)

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .acceptance_requirements import acceptance_inventory


def bind_final_acceptance_scopes(
    tasks: list[dict[str, Any]], root: Path | None, feature: str | None
) -> None:
    """Bind final acceptance to its explicit immutable inventory or reviewed-spec obligation."""
    for task in tasks:
        if not is_final_acceptance_task(task) or root is None or not feature:
            continue
        if task.get("acceptance_binding") == "reviewed-spec":
            task["required_evidence"].append("spec_review_receipt_path")
            continue
        inventory = [item.model_dump(mode="json") for item in acceptance_inventory(root, feature)]
        task.setdefault("expected_evidence", {})["acceptance_inventory"] = inventory
        if any(item["evidence_kind"] == "review" for item in inventory):
            task["required_evidence"].append("acceptance_review_receipt_path")


def is_final_acceptance_task(task: Mapping[str, Any]) -> bool:
    """Use existing resolved task metadata, never infer finality from prose or command names."""
    return (
        task.get("evidence_kind") == "execution"
        and task.get("acceptance_scope") == "feature"
        and task.get("evidence_expected_outcome") != "red"
    )


def verify_acceptance_evidence(
    task: Mapping[str, Any],
    evidence: Mapping[str, Any],
    receipt: Path,
    root: Path,
    feature: str,
) -> list[str]:
    """Require all declared execution AND review evidence without runtime-certifying reviews."""
    from .execution_evidence import verify_execution_receipt

    inventory = acceptance_inventory(root, feature)
    expected = task.get("expected_evidence", {})
    if task.get("acceptance_binding") == "reviewed-spec":
        if missing := _spec_review_missing(expected, evidence, root, feature):
            return missing
    else:
        frozen = expected.get("acceptance_inventory") if isinstance(expected, dict) else None
        if frozen != [item.model_dump(mode="json") for item in inventory]:
            return ["acceptance_declarations_changed_recompile_required"]
    if not inventory:
        return ["feature_acceptance_scope_empty"]
    runtime_ids = tuple(
        item.requirement_id for item in inventory if item.evidence_kind == "execution"
    )
    result = verify_execution_receipt(receipt, root, feature, required_acs=runtime_ids)
    missing = [] if result.valid else list(result.gaps)
    if any(item.evidence_kind == "review" for item in inventory):
        missing.extend(_review_acceptance_missing(expected, evidence, root, feature))
    return missing


def _spec_review_missing(
    expected: Mapping[str, Any], evidence: Mapping[str, Any], root: Path, feature: str
) -> list[str]:
    """Resolve a current, complete spec-kind review using the contract's reviewer identity."""
    from .semantic.review_api import verify_feature_review

    raw = evidence.get("spec_review_receipt_path")
    if not isinstance(raw, str) or not raw:
        return ["spec_review_receipt_path"]
    model = expected.get("reviewer_model", "")
    if model in {"", "unknown", "default"}:
        return ["acceptance_reviewer_model_required"]
    path = root / raw
    path.resolve().relative_to(root.resolve())
    budget = expected.get("review_max_chars")
    valid = verify_feature_review(
        root,
        feature,
        path,
        model=str(model),
        max_chars=budget if isinstance(budget, int) else None,
        expected_kind="spec",
    )
    return [] if valid else ["spec_review_incomplete_or_stale"]


def _review_acceptance_missing(
    expected: Mapping[str, Any], evidence: Mapping[str, Any], root: Path, feature: str
) -> list[str]:
    from .semantic.acceptance_review import verify_acceptance_review

    raw = evidence.get("acceptance_review_receipt_path")
    if not isinstance(raw, str) or not raw:
        return ["acceptance_review_receipt_path"]
    model = expected.get("reviewer_model", "")
    if model in {"", "unknown", "default"}:
        return ["acceptance_reviewer_model_required"]
    path = root / raw
    path.resolve().relative_to(root.resolve())
    budget = expected.get("review_max_chars")
    valid = verify_acceptance_review(
        root, feature, path, model=str(model), max_chars=budget if isinstance(budget, int) else None
    )
    return [] if valid else ["acceptance_review_incomplete_or_stale"]


def archived_policy2_evidence_errors(artifact: Mapping[str, Any], root: Path) -> list[str]:
    """Do not let deleting receipts or state tasks erase immutable acceptance obligations."""
    from .evidence_policy import current_contract_integrity_error, typed_evidence_missing

    contract = artifact.get("evidence_contract")
    if isinstance(contract, dict) and contract.get("evidence_policy_version") != artifact.get(
        "evidence_policy_version"
    ):
        return ["policy2_archive_policy_mismatch"]
    if artifact.get("evidence_policy_version") != "2":
        return []
    if not isinstance(contract, dict):
        return ["policy2_evidence_contract_required"]
    error = current_contract_integrity_error(contract)
    if error:
        return [error]
    if contract.get("goal_hash") != artifact.get("goal_hash"):
        return ["policy2_archive_contract_hash_mismatch"]
    for outer, inner in (
        ("feature", "feature"),
        ("flags", "normalized_flags"),
        ("command", "command"),
    ):
        if artifact.get(outer) != contract.get(inner):
            return [f"policy2_archive_contract_mismatch:{outer}"]
    goal = artifact.get("goal", {})
    tasks = {task.get("id"): task for task in goal.get("tasks", []) if isinstance(task, dict)}
    errors: list[str] = []
    for declaration in contract.get("tasks", []):
        if declaration.get("id") == "archive.run":
            continue
        state = tasks.get(declaration.get("id"), {})
        if not state:
            errors.append(f"policy2_declared_task_missing:{declaration.get('id')}")
        if state.get("status") != "complete":
            continue  # Existing goal-incomplete evaluation preserves pending-task drift.
        evidence = state.get("accepted_evidence")
        errors.extend(
            typed_evidence_missing(
                declaration,
                evidence if isinstance(evidence, dict) else {},
                contract=contract,
                project_root=root,
            )
        )
    return errors


def archived_policy2_path_error(artifact: Mapping[str, Any], path: Path) -> str | None:
    """A produced policy2 path keeps its policy even if mutable JSON mirrors are removed."""
    from .evidence_policy import contract_evidence_policy, current_contract_integrity_error

    name = path.resolve(strict=True).name  # A legacy-named symlink cannot remove path authority.
    if not name.endswith("-policy2.json"):
        return None
    contract = artifact.get("evidence_contract")
    if artifact.get("evidence_policy_version") != "2" or not isinstance(contract, dict):
        return "policy2_path_requires_immutable_contract"
    if contract_evidence_policy(contract) != "2":
        return "policy2_path_requires_current_contract"
    error = current_contract_integrity_error(contract)
    if error:
        return error
    if not name.endswith(f"-{str(contract.get('goal_hash', ''))[:8]}-policy2.json"):
        return "policy2_path_contract_hash_mismatch"
    if not name.startswith(f"{contract.get('command')}-"):
        return "policy2_path_command_mismatch"
    return None
