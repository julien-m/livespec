"""Goal payload responsibilities behind the public contract facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import goal_contracts as _contracts

__all__ = [
    "_bind_task_review_identity",
    "_goal_expectation_payload",
    "_goal_payload",
    "_goal_rules",
    "_goal_runtime",
]


def _goal_payload(
    *,
    command: str,
    expectations: _contracts.ExpectationsFile,
    livespec_root: Path,
    project_root: Path,
    feature: str | None,
    flags: str | list[str] | tuple[str, ...] | None,
) -> dict[str, Any]:
    skill_path = livespec_root / ".agent-sync" / "skills" / command / "SKILL.md"
    normalized_flags = _contracts.normalize_goal_flags(flags)
    runtime, execution_tasks, definition_of_done = _contracts._goal_runtime(
        command, project_root, feature, skill_path, normalized_flags
    )
    conventions, hooks, qe_analysis = _payload_extensions(
        command, expectations, project_root, feature, normalized_flags, livespec_root
    )
    tasks = _compiled_payload_tasks(
        command,
        project_root,
        feature,
        skill_path,
        normalized_flags,
        runtime,
        execution_tasks,
        definition_of_done,
        conventions,
        hooks,
        qe_analysis,
    )
    payload = {
        **_goal_base_payload(command, feature, normalized_flags),
        "runtime_context": runtime,
        "execution_tasks": execution_tasks,
        "tasks": tasks,
        "internal_command_invocations": _contracts._extract_internal_command_invocations(
            skill_path
        ),
        "hooks": hooks,
        **({"qe_analysis": qe_analysis} if qe_analysis is not None else {}),
        "conventions": conventions,
        "definition_of_done": definition_of_done,
        **_contracts._goal_expectation_payload(expectations, project_root, livespec_root),
    }
    if command == "spec-init":
        payload["project_root"] = project_root.resolve().as_posix()
    return payload


def _goal_expectation_payload(
    expectations: _contracts.ExpectationsFile,
    project_root: Path,
    livespec_root: Path,
) -> dict[str, Any]:
    return {
        "expectations": {
            "command": expectations.command,
            "contract_version": expectations.contract_version,
            "last_reviewed": expectations.last_reviewed,
            "source_path": _contracts._stable_path(
                expectations.source_path,
                project_root=project_root,
                livespec_root=livespec_root,
            ),
        },
        "expectation_sections": {
            "purpose": _contracts._normalize_section_lines(
                expectations.prose_sections["1. Purpose"]
            ),
            "preconditions": _contracts._normalize_section_lines(
                expectations.prose_sections["2. Preconditions"]
            ),
            "filesystem_effects": _contracts._normalize_section_lines(
                expectations.prose_sections["4. Filesystem Effects"]
            ),
            "produced_artifacts": _contracts._normalize_section_lines(
                expectations.prose_sections["6. Produced Artifacts"]
            ),
            "post_run_checks": _contracts._normalize_section_lines(
                expectations.prose_sections["10. Post-run Checks"]
            ),
        },
        "verify_rules": _expectation_verify_rules(expectations),
    }


def _bind_task_review_identity(
    tasks: list[dict[str, Any]],
    normalized_flags: list[str],
    feature: str | None,
) -> None:
    review_model = next(
        (flag.split("=", 1)[1] for flag in normalized_flags if flag.startswith("--model=")), ""
    )
    for task in tasks:
        expected = task.setdefault("expected_evidence", {})
        expected["reviewer_model"] = review_model
        budget = next(
            (
                flag.split("=", 1)[1]
                for flag in normalized_flags
                if flag.startswith("--review-max-chars=")
            ),
            None,
        )
        expected["review_max_chars"] = int(budget) if budget else None
        if not expected.get("feature_slug"):
            expected["feature_slug"] = feature


def _goal_runtime(
    command: str,
    project_root: Path,
    feature: str | None,
    skill_path: Path,
    normalized_flags: list[str],
) -> tuple[dict[str, Any], list[str], list[str]]:
    is_visual, visual_feature_slugs = _runtime_visual_scope(
        command, project_root, feature, normalized_flags
    )
    has_penflow = _contracts._detect_penflow(project_root)
    execution_tasks = _contracts._extract_execution_tasks(
        skill_path,
        normalized_flags=normalized_flags,
        is_visual=is_visual,
        has_penflow=has_penflow,
    )
    active_branches = _contracts._active_execution_task_branches(
        normalized_flags=normalized_flags,
        command=command,
        is_visual=is_visual,
        visual_enabled="--no-visual" not in normalized_flags,
        has_penflow=has_penflow,
        audit_only="--audit-only" in normalized_flags,
        no_generate="--no-generate" in normalized_flags,
    )
    definition_of_done = [
        _contracts.strip_evidence_marker(item)
        for item in _contracts._extract_definition_of_done(
            skill_path, active_branches=active_branches
        )
    ]
    return (
        {
            "is_visual_feature": is_visual,
            "has_penflow": has_penflow,
            "visual_feature_slugs": visual_feature_slugs,
        },
        execution_tasks,
        definition_of_done,
    )


def _goal_rules() -> dict[str, Any]:
    return {
        "completion_actor": "goal",
        "proof_required_for_each_task": True,
        "worker_may_mark_tasks_complete": False,
        "missing_evidence_status": "REJECTED_NEEDS_ACTION",
        "blocked_requires_canonical_line": True,
    }


def _compiled_payload_tasks(
    command: str,
    project_root: Path,
    feature: str | None,
    skill_path: Path,
    normalized_flags: list[str],
    runtime: dict[str, Any],
    execution_tasks: list[str],
    definition_of_done: list[str],
    conventions: dict[str, Any],
    hooks: dict[str, Any],
    qe_analysis: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    tasks = _contracts._build_goal_tasks(
        command=command,
        execution_tasks=execution_tasks,
        definition_of_done=definition_of_done,
        visual_feature_slugs=runtime["visual_feature_slugs"],
        conventions=conventions,
        conventions_gate_exists=_contracts.gates_path(project_root).exists(),
        hooks=hooks,
        qe_analysis=qe_analysis,
    )
    _contracts.apply_evidence_policy(tasks, skill_path, project_root=project_root, feature=feature)
    if command == "spec-fix":
        from .fix_acceptance_scope import _bind_fix_acceptance_scope

        _bind_fix_acceptance_scope(tasks, project_root, feature, normalized_flags)
    _contracts._bind_task_review_identity(tasks, normalized_flags, feature)
    return tasks


def _payload_extensions(
    command: str,
    expectations: _contracts.ExpectationsFile,
    project_root: Path,
    feature: str | None,
    normalized_flags: list[str],
    livespec_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    conventions = _contracts._compile_conventions_payload(
        command=command,
        expectations=expectations,
        project_root=project_root,
        feature=feature,
        normalized_flags=normalized_flags,
    )
    hooks = _contracts._compile_hooks_payload(
        command=command,
        livespec_root=livespec_root,
        project_root=project_root,
        feature=feature,
    )
    qe_analysis = _contracts._compile_qe_analysis_payload(
        command=command, livespec_root=livespec_root
    )
    return conventions, hooks, qe_analysis


def _expectation_verify_rules(expectations: _contracts.ExpectationsFile) -> dict[str, Any]:
    return {
        "must": _contracts._canonical_rules(expectations.verify.must),
        "may": _contracts._canonical_rules(expectations.verify.may),
        "must_not": _contracts._canonical_rules(expectations.verify.must_not),
        "when": [
            {
                "flag": branch.flag,
                "must": _contracts._canonical_rules(branch.must),
                "may": _contracts._canonical_rules(branch.may),
                "must_not": _contracts._canonical_rules(branch.must_not),
                # Only emit replace_base when True so existing contracts/hashes
                # for unaffected commands stay byte-identical (retro-compat).
                **({"replace_base": True} if branch.replace_base else {}),
            }
            for branch in expectations.verify.when
        ],
    }


def _goal_base_payload(
    command: str, feature: str | None, normalized_flags: list[str]
) -> dict[str, Any]:
    return {
        "evidence_policy_version": _contracts.EVIDENCE_POLICY_VERSION,
        "schema_version": _contracts.GOAL_CONTRACT_VERSION,
        "command": command,
        "feature": feature,
        "normalized_flags": normalized_flags,
        "mode": "enforced",
        "rules": _contracts._goal_rules(),
    }


def _runtime_visual_scope(
    command: str,
    project_root: Path,
    feature: str | None,
    normalized_flags: list[str],
) -> tuple[bool, list[str]]:
    is_visual = _contracts._detect_visual_feature(project_root, feature)
    if not is_visual and _contracts._is_all_feature_spec_check(
        command=command,
        feature=feature,
        normalized_flags=normalized_flags,
    ):
        is_visual = _contracts._detect_any_visual_feature(project_root)
    visual_feature_slugs = [feature] if feature and is_visual else []
    if not visual_feature_slugs and _contracts._is_all_feature_spec_check(
        command=command,
        feature=feature,
        normalized_flags=normalized_flags,
    ):
        visual_feature_slugs = _contracts._detect_visual_feature_slugs(project_root)
    return is_visual, visual_feature_slugs
