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
    if "pixel regression" in lowered:
        return "visual.pixel_regression"
    # @spec FR-005: route finalize wording to the finalize.registry family
    #   — .specs/features/058-deterministic-finalization/spec.md#fr-005
    if "finalize registry" in lowered or "livespec finalize" in lowered:
        return "finalize.registry"
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
    # Typed execution/review rows replace generic proof with their receipt (evidence policy).
    if task_id == "visual.design_fidelity":
        return _contracts.VISUAL_DESIGN_REQUIRED_EVIDENCE
    if task_id == "visual.pixel_regression":
        return ("visual_evidence_receipt_path",)
    if task_id == "finalize.registry":
        return _contracts.FINALIZE_REQUIRED_EVIDENCE
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
    return _contracts.GENERIC_REPAIR_ACTIONS
