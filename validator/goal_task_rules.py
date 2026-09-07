"""Goal task rules responsibilities behind the public contract facade."""

from __future__ import annotations

import re

from . import goal_contracts as _contracts

__all__ = [
    "_invalid_substitutes_for_task",
    "_repair_actions_for_task",
    "_required_evidence_for_task",
    "_slugify_task_id",
    "_task_id_for_description",
]


def _task_id_for_description(
    command: str,
    category: str,
    ordinal: int,
    description: str,
) -> str:
    lowered = description.lower()
    if "design fidelity" in lowered:
        return "visual.design_fidelity"
    if "visual-gate validate" in lowered:
        return "visual.gate_validate"
    if "pixel regression" in lowered:
        return "visual.pixel_regression"
    if "staleness gate" in lowered or "baseline.manifest" in lowered:
        return "visual.baseline_manifest"
    # @spec FR-005: route finalize wording to the finalize.registry family
    #   — .specs/features/058-deterministic-finalization/spec.md#fr-005
    if "finalize registry" in lowered or "livespec finalize" in lowered:
        return "finalize.registry"
    if "penflow contract status" in lowered:
        return "penflow.contract_status"
    if "penflow drift" in lowered:
        return "penflow.drift"
    if "compare-report" in lowered:
        return "penflow.compare_report"
    if "spawn independent native sub-agent" in lowered and "/spec-fix" in lowered:
        return "fix.child_goal.spec_fix"
    if "spawn independent native sub-agent" in lowered and "/spec-check" in lowered:
        return "fix.child_goal.spec_check"
    if "capture child" in lowered and "/spec-fix" in lowered:
        return "fix.child_goal.capture"
    if "inspect child goal" in lowered:
        return "fix.child_goal.inspect"
    prefix = "dod" if category == "definition_of_done" else "task"
    slug = _contracts._slugify_task_id(description)
    if not slug:
        slug = command
    return f"{prefix}.{ordinal:03d}.{slug}"


def _slugify_task_id(description: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", description.lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    return slug[:48].strip("_")


def _required_evidence_for_task(
    task_id: str, description: str, *, is_visual: bool = True
) -> tuple[str, ...]:
    lowered = description.lower()
    if task_id == "visual.design_fidelity":
        return _contracts.VISUAL_DESIGN_REQUIRED_EVIDENCE
    if task_id == "visual.pixel_regression":
        return ("visual_evidence_receipt_path",)
    if task_id == "finalize.registry":
        return _contracts.FINALIZE_REQUIRED_EVIDENCE
    if task_id.startswith("fix.child_goal"):
        return (
            "child_goal_hash_recorded",
            "child_contract_file_exists",
            "child_state_file_exists",
            "child_final_status_recorded",
        )
    if "visual-gate validate" in lowered:
        return (
            "command_exit_code_recorded",
            "json_verdict_recorded",
            "missing_artifacts_list_recorded",
        )
    if is_visual and "penflow" in lowered:
        return (
            "penflow_artifact_path_exists",
            "penflow_status_or_report_recorded",
        )
    if is_visual and any(word in lowered for word in ("baseline", "mockup", "screenshot")):
        return (
            "artifact_path_exists",
            "hash_or_manifest_status_recorded",
        )
    return _contracts.GENERIC_REQUIRED_EVIDENCE


def _invalid_substitutes_for_task(task_id: str, description: str) -> tuple[str, ...]:
    if task_id == "visual.design_fidelity":
        return _contracts.VISUAL_DESIGN_INVALID_SUBSTITUTES
    if task_id == "visual.pixel_regression":
        return ("worker_declared_diff_without_receipt",)
    if task_id == "finalize.registry":
        return _contracts.FINALIZE_INVALID_SUBSTITUTES
    if "visual" in description.lower():
        return ("verbal_visual_confirmation_without_artifact",)
    return ()


def _repair_actions_for_task(task_id: str, description: str) -> tuple[str, ...]:
    lowered = description.lower()
    if task_id == "visual.design_fidelity":
        return _contracts.VISUAL_DESIGN_REPAIR_ACTIONS
    if task_id == "visual.pixel_regression":
        return (
            "run `livespec visual-gate certify --feature <slug> --command <command> "
            "--target <target> --run-id <run-id> --json` and submit the generated "
            "receipt.json path",
        )
    if task_id == "finalize.registry":
        return _contracts.FINALIZE_REPAIR_ACTIONS
    if task_id.startswith("fix.child_goal"):
        return (
            "spawn the required independent native sub-agent and let it create its own goal",
            "record the child goal hash, contract file, state file, final status, and artifacts",
        )
    if "visual-gate validate" in lowered:
        return (
            "run the visual gate command exactly as specified",
            "if exit 7 occurs, create the listed missing artifacts and rerun before proving",
        )
    if "penflow" in lowered:
        return (
            "run the required Penflow command or create the missing Penflow prerequisite",
            "record the concrete Penflow report path and final status",
        )
    return _contracts.GENERIC_REPAIR_ACTIONS
