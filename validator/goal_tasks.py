"""Goal tasks responsibilities behind the public contract facade."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from . import goal_contracts as _contracts

__all__ = [
    "_build_goal_tasks",
    "_goal_row_tasks",
    "_task_proof_requirements",
    "_task_required_conventions",
    "_unique_task_id",
]


def _build_goal_tasks(
    *,
    command: str,
    execution_tasks: list[str],
    definition_of_done: list[str],
    visual_feature_slugs: list[str],
    conventions: Mapping[str, object],
    conventions_gate_exists: bool,
    hooks: Mapping[str, object],
    qe_analysis: Mapping[str, object] | None,
) -> list[dict[str, Any]]:
    """Convert command task prose into enforced proof tasks."""
    # Build base proof tasks first, then layer optional convention evidence onto
    # every task when conventions were selected.
    rows: list[tuple[str, str]] = [("execution", task) for task in execution_tasks]
    rows.extend(("definition_of_done", item) for item in definition_of_done)
    if not rows:
        rows.append(("execution", "Follow command SKILL.md phases and expectations."))

    tasks: list[dict[str, Any]] = []
    seen: set[str] = set()
    required_conventions = _contracts._task_required_conventions(conventions)
    required_convention_domains: list[str] = []
    required_convention_sources: list[str] = []
    if required_conventions is not None:
        required_convention_domains = cast(list[str], required_conventions["domains"])
        required_convention_sources = cast(list[str], required_conventions["source_paths"])
    tasks.extend(_initial_goal_tasks(command, hooks, qe_analysis))
    start_ordinal = len(tasks) + 1
    for ordinal, (category, description) in enumerate(rows, start_ordinal):
        tasks.extend(
            _contracts._goal_row_tasks(
                command,
                category,
                ordinal,
                description,
                seen,
                visual_feature_slugs,
                required_conventions,
                required_convention_domains,
                required_convention_sources,
                conventions_gate_exists,
            )
        )
    next_archive_ordinal = max((int(task["ordinal"]) for task in tasks), default=0) + 1
    tasks.append(_contracts._archive_run_task(command=command, next_ordinal=next_archive_ordinal))
    return tasks


def _goal_row_tasks(
    command: str,
    category: str,
    ordinal: int,
    description: str,
    seen: set[str],
    visual_feature_slugs: list[str],
    required_conventions: _contracts.RequiredConventions | None,
    required_convention_domains: list[str],
    required_convention_sources: list[str],
    conventions_gate_exists: bool,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    task_id, feature_targets = _row_identity_and_targets(
        command, category, ordinal, description, seen, visual_feature_slugs
    )
    for feature_slug in feature_targets:
        effective_id, effective_description = _feature_task_identity(
            task_id, description, feature_slug, len(feature_targets), seen, ordinal
        )
        required_evidence, repair_actions = _contracts._task_proof_requirements(
            task_id,
            description,
            bool(visual_feature_slugs),
            required_conventions,
            required_convention_domains,
            required_convention_sources,
            conventions_gate_exists,
            command,
        )
        task: dict[str, Any] = {
            "id": effective_id,
            "ordinal": ordinal,
            "category": category,
            "description": effective_description,
            "required_evidence": required_evidence,
            "invalid_substitutes": list(
                _contracts._invalid_substitutes_for_task(task_id, description)
            ),
            "repair_if_missing": repair_actions,
            "completion_actor": "goal",
            "expected_evidence": {
                "command": command,
                "feature_slug": feature_slug,
            },
        }
        if required_conventions is not None:
            task["required_conventions"] = required_conventions
        tasks.append(task)
    return tasks


def _task_proof_requirements(
    task_id: str,
    description: str,
    is_visual: bool,
    required_conventions: _contracts.RequiredConventions | None,
    required_convention_domains: list[str],
    required_convention_sources: list[str],
    conventions_gate_exists: bool,
    command: str,
) -> tuple[list[str], list[str]]:
    required_evidence = list(
        _contracts._required_evidence_for_task(task_id, description, is_visual=is_visual)
    )
    repair_actions = list(_contracts._repair_actions_for_task(task_id, description))
    if required_conventions is not None:
        # @spec FR-002: Convention proof fields, FR-004: Convention repair actions
        #   — .specs/features/053-goal-tasks-replay-required-conventions-per-step/spec.md#fr-002  # noqa: E501 - @spec anchor path must stay on one line
        required_evidence.extend(
            [
                "convention_domains_recorded",
                "convention_sources_read",
                "conventions_applied_to_output",
            ]
        )
        repair_actions.append(
            "Read and apply conventions before retrying: "
            f"domains={', '.join(required_convention_domains)}; "
            f"sources={', '.join(required_convention_sources)}."
        )
    if conventions_gate_exists and command in _contracts._CONVENTIONS_GATED_COMMANDS:
        required_evidence.extend(_contracts.CONVENTIONS_REQUIRED_EVIDENCE)
        repair_actions.append(
            f"Run `{_contracts.CONVENTIONS_VERIFY_COMMAND}` and submit the generated "
            "conventions receipt path."
        )
    return required_evidence, repair_actions


# @spec FR-001: Per-task convention payload
#   — .specs/features/053-goal-tasks-replay-required-conventions-per-step/spec.md#fr-001
def _task_required_conventions(
    conventions: Mapping[str, object],
) -> _contracts.RequiredConventions | None:
    selected_domains = [
        domain
        for domain in cast(list[object], conventions.get("selected_domains") or [])
        if isinstance(domain, dict)
    ]
    if not selected_domains:
        return None
    domains = [
        str(domain["name"]) for domain in selected_domains if isinstance(domain.get("name"), str)
    ]
    source_paths = [
        str(path)
        for domain in selected_domains
        for path in cast(list[object], domain.get("paths") or [])
        if isinstance(path, str)
    ]
    if not domains or not source_paths:
        return None
    return {
        "mode": "read_apply",
        "domains": domains,
        "source_paths": source_paths,
    }


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
