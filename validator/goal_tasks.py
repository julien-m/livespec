"""Goal tasks responsibilities behind the public contract facade."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import goal_contracts as _contracts
from .goal_outcome import conventions_gate_task, outcome_task

__all__ = [
    "_build_goal_tasks",
    "_goal_row_tasks",
    "_unique_task_id",
    "finalize_required_tasks",
]

# Families whose proof is a verifiable receipt or resolved context, never prose.
_RECEIPT_FAMILIES: tuple[str, ...] = (
    "hooks.before",
    "qe.analysis",
    "visual.design_fidelity",
    "visual.pixel_regression",
    "finalize.registry",
)


def _build_goal_tasks(
    *,
    command: str,
    execution_tasks: list[str],
    definition_of_done: list[str],
    visual_feature_slugs: list[str],
    hooks: Mapping[str, object],
    qe_analysis: Mapping[str, object] | None,
) -> list[dict[str, Any]]:
    """Convert command inventory rows into candidate tasks before evidence classification."""
    rows: list[tuple[str, str]] = [("execution", task) for task in execution_tasks]
    rows.extend(("definition_of_done", item) for item in definition_of_done)
    tasks: list[dict[str, Any]] = _initial_goal_tasks(command, hooks, qe_analysis)
    seen: set[str] = set()
    for ordinal, (category, description) in enumerate(rows, len(tasks) + 1):
        tasks.extend(
            _contracts._goal_row_tasks(
                command, category, ordinal, description, seen, visual_feature_slugs
            )
        )
    return tasks


# @spec FR-002: Required receipts only, FR-006: One conventions gate
#   — .specs/features/081-lightweight-outcome-goals/spec.md#fr-002
def finalize_required_tasks(
    command: str,
    tasks: list[dict[str, Any]],
    *,
    stop: Mapping[str, Any],
    conventions_gated: bool,
) -> list[dict[str, Any]]:
    """Keep high-value tasks, append conventions/outcome/archive and renumber ordinals.

    Args:
        command: Canonical command name.
        tasks: Candidate tasks after evidence-policy classification.
        stop: Compiled stop condition.
        conventions_gated: Whether a feature-scope conventions receipt is required.

    Returns:
        Required tasks with contiguous ordinals starting at 1.
    """
    required = [
        task
        for task in tasks
        if str(task["id"]).startswith(_RECEIPT_FAMILIES)
        or task.get("evidence_kind") in ("execution", "review")
    ]
    if conventions_gated:
        required.append(conventions_gate_task(command=command, ordinal=0))
    required.append(outcome_task(command=command, ordinal=0, condition=stop))
    required.append(_contracts._archive_run_task(command=command, next_ordinal=0))
    for ordinal, task in enumerate(required, 1):
        task["ordinal"] = ordinal
        task.setdefault("evidence_kind", "documentary")
    return required


def _goal_row_tasks(
    command: str,
    category: str,
    ordinal: int,
    description: str,
    seen: set[str],
    visual_feature_slugs: list[str],
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    task_id, feature_targets = _row_identity_and_targets(
        command, category, ordinal, description, seen, visual_feature_slugs
    )
    for feature_slug in feature_targets:
        effective_id, effective_description = _feature_task_identity(
            task_id, description, feature_slug, len(feature_targets), seen, ordinal
        )
        is_visual = bool(visual_feature_slugs)
        tasks.append(
            {
                "id": effective_id,
                "ordinal": ordinal,
                "category": category,
                "description": effective_description,
                "required_evidence": list(
                    _contracts._required_evidence_for_task(
                        task_id, description, is_visual=is_visual
                    )
                ),
                "invalid_substitutes": list(
                    _contracts._invalid_substitutes_for_task(task_id, description)
                ),
                "repair_if_missing": list(
                    _contracts._repair_actions_for_task(task_id, description)
                ),
                "completion_actor": "goal",
                "expected_evidence": {"command": command, "feature_slug": feature_slug},
            }
        )
    return tasks


def _unique_task_id(base_id: str, seen: set[str], ordinal: int) -> str:
    if base_id not in seen:
        seen.add(base_id)
        return base_id
    task_id = f"{base_id}.{ordinal:03d}"
    seen.add(task_id)
    return task_id


def _initial_goal_tasks(
    command: str,
    hooks: Mapping[str, object],
    qe_analysis: Mapping[str, object] | None,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    before_hook = hooks.get("before")
    before_hook_context = before_hook if isinstance(before_hook, dict) else {}
    before_hook_context_text = before_hook_context.get("context")
    if isinstance(before_hook_context_text, str) and before_hook_context_text.strip():
        tasks.append(
            _contracts._hooks_before_task(command=command, hook_context=before_hook_context)
        )
    if qe_analysis is not None:
        tasks.append(_contracts._qe_analysis_task(command=command, next_ordinal=len(tasks) + 1))
    return tasks


def _feature_task_identity(
    task_id: str,
    description: str,
    feature_slug: str | None,
    target_count: int,
    seen: set[str],
    ordinal: int,
) -> tuple[str, str]:
    effective_id = task_id
    effective_description = description
    if feature_slug is not None:
        effective_description = f"{description} [feature: {feature_slug}]"
    if feature_slug is not None and target_count > 1:
        effective_id = _contracts._unique_task_id(
            f"{task_id}.{_contracts._slugify_task_id(feature_slug)}",
            seen,
            ordinal,
        )
    return effective_id, effective_description


def _row_identity_and_targets(
    command: str,
    category: str,
    ordinal: int,
    description: str,
    seen: set[str],
    visual_feature_slugs: list[str],
) -> tuple[str, list[str | None]]:
    task_id = _contracts._unique_task_id(
        _contracts._task_id_for_description(command, category, ordinal, description),
        seen,
        ordinal,
    )
    feature_targets: list[str | None] = [None]
    if task_id in {"visual.design_fidelity", "visual.pixel_regression"}:
        feature_targets = list(visual_feature_slugs) or [None]
    return task_id, feature_targets
