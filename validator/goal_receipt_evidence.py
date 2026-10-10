"""Goal receipt evidence responsibilities behind the public contract facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import goal_contracts as _contracts
from .evidence_policy import SUPPORTED_EVIDENCE_POLICIES

__all__ = [
    "_nonempty_string_list",
    "_valid_qe_boundary_note",
    "_validate_hooks_before_evidence",
    "_validate_qe_analysis_evidence",
    "_validate_task_evidence",
    "_validate_visual_receipt_evidence",
]


def _validate_task_evidence(
    task: dict[str, Any],
    evidence: dict[str, Any],
    *,
    contract: dict[str, Any],
    project_root: Path | None,
) -> dict[str, Any]:
    policy = _contracts.contract_evidence_policy(contract)
    if policy is not None and policy not in SUPPORTED_EVIDENCE_POLICIES:
        return {
            "status": "REJECTED_NEEDS_ACTION",
            "accepted": False,
            "missing_evidence": ["unknown_evidence_policy_version"],
            "invalid_substitutes": [],
            "required_actions": ["Use a supported evidence policy."],
        }
    task_id = str(task["id"])
    if task_id == "visual.design_fidelity" or task_id.startswith(
        ("visual.design_fidelity.", "visual.pixel_regression")
    ):
        return _contracts._validate_visual_receipt_evidence(
            task,
            evidence,
            contract=contract,
            project_root=project_root,
        )
    if task_id == "finalize.registry" or task_id.startswith("finalize.registry."):
        return _contracts._validate_finalize_receipt_evidence(
            task,
            evidence,
            contract=contract,
            project_root=project_root,
        )
    if _task_family_matches(task_id, _contracts.ARCHIVE_RUN_TASK_ID):
        return _contracts._validate_archive_run_evidence(
            task,
            evidence,
            contract=contract,
            project_root=project_root,
        )
    if _task_family_matches(task_id, _contracts.HOOKS_BEFORE_TASK_ID):
        return _contracts._validate_hooks_before_evidence(task, evidence)
    if _task_family_matches(task_id, _contracts.QE_ANALYSIS_TASK_ID):
        return _contracts._validate_qe_analysis_evidence(task, evidence)
    return _contracts._validate_generic_evidence(
        task,
        evidence,
        contract=contract,
        project_root=project_root,
    )


def _validate_hooks_before_evidence(
    task: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    missing: list[str] = []
    invalid: list[str] = []
    expected = dict(task.get("expected_evidence") or {})

    expected_command = expected.get("hook_resolution_command")
    actual_command = evidence.get("hook_resolution_command")
    if not isinstance(actual_command, str) or not actual_command.strip():
        missing.append("hook_resolution_command")
    elif isinstance(expected_command, str) and actual_command != expected_command:
        missing.append("hook_resolution_command_matches_contract")

    expected_sha = expected.get("resolved_hook_context_sha256")
    actual_sha = evidence.get("resolved_hook_context_sha256")
    if not isinstance(actual_sha, str) or not actual_sha.strip():
        missing.append("resolved_hook_context_sha256")
    elif isinstance(expected_sha, str) and actual_sha != expected_sha:
        missing.append("resolved_hook_context_sha256_matches_contract")

    if evidence.get("hook_context_applied") is not True:
        missing.append("hook_context_applied")

    if evidence.get("output") or evidence.get("summary") or evidence.get("prose"):
        invalid.append("manual_integration_summary")
    if evidence.get("config_file_exists"):
        invalid.append("config_file_exists_without_resolved_context")

    accepted = not missing and not invalid
    return {
        "status": "ACCEPTED" if accepted else "REJECTED_NEEDS_ACTION",
        "accepted": accepted,
        "missing_evidence": missing,
        "invalid_substitutes": invalid,
        "required_actions": list(task["repair_if_missing"]),
    }


# @spec FR-005: Reject generic QE evidence, FR-006: Reject skill/config substitutes
#   — .specs/features/071-qe-analysis-native-module/spec.md#fr-005
def _validate_qe_analysis_evidence(
    task: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    # Validate separate passes so callers get missing fields and invalid substitutes together.
    missing: list[str] = []
    invalid: list[str] = []

    if evidence.get("output") or evidence.get("summary") or evidence.get("success_criteria_met"):
        invalid.append("generic_quality_claim")
    if evidence.get("skill") == "qe-analysis" or evidence.get("qe_analysis_skill_invoked"):
        invalid.append("skill_global_qe_analysis_invocation")
    if evidence.get("config_path") or evidence.get("user_config_qe_analysis"):
        invalid.append("user_config_qe_analysis_only")

    for required in _contracts.QE_ANALYSIS_REQUIRED_EVIDENCE:
        value = evidence.get(required)
        if required == "qe_boundary_note":
            if not _contracts._valid_qe_boundary_note(value):
                missing.append(required)
            continue
        if not _contracts._nonempty_string_list(value):
            missing.append(required)

    accepted = not missing and not invalid
    return {
        "status": "ACCEPTED" if accepted else "REJECTED_NEEDS_ACTION",
        "accepted": accepted,
        "missing_evidence": missing,
        "invalid_substitutes": invalid,
        "required_actions": list(task["repair_if_missing"]),
    }


def _nonempty_string_list(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def _valid_qe_boundary_note(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    lowered = value.lower()
    return any(marker in lowered for marker in ("review", "audit", "test"))


def _validate_visual_receipt_evidence(
    task: dict[str, Any],
    evidence: dict[str, Any],
    *,
    contract: dict[str, Any],
    project_root: Path | None,
) -> dict[str, Any]:
    missing: list[str] = []
    invalid = _visual_invalid_substitutes(evidence)

    receipt_path = evidence.get("visual_evidence_receipt_path")
    if not isinstance(receipt_path, str) or not receipt_path.strip():
        missing.append("visual_evidence_receipt_path")
    elif project_root is None:
        missing.append("project_root_for_receipt_verification")
    else:
        expected_feature, expected_command = _visual_expected_scope(task, contract)
        expected_target_raw = evidence.get("target")
        expected_target = expected_target_raw if isinstance(expected_target_raw, str) else None
        try:
            receipt = _contracts.verify_visual_receipt(
                Path(receipt_path),
                project_root=project_root,
                expected_feature_slug=expected_feature,
                expected_command=expected_command,
                expected_target=expected_target,
            )
        except (OSError, _contracts.VisualReceiptError) as exc:
            missing.append(f"visual_evidence_receipt_valid:{exc}")
        else:
            required_kind = (
                "mockup_runtime"
                if str(task["id"]).startswith("visual.design_fidelity")
                else "baseline_runtime"
            )
            if receipt.verdict != "PASS":
                missing.append("visual_evidence_receipt_verdict_pass")
            if not any(c.comparison_kind == required_kind for c in receipt.comparisons):
                missing.append(f"{required_kind}_comparison_exists")

    accepted = not missing and not invalid
    return {
        "status": "ACCEPTED" if accepted else "REJECTED_NEEDS_ACTION",
        "accepted": accepted,
        "missing_evidence": missing,
        "invalid_substitutes": invalid,
        "required_actions": list(task["repair_if_missing"]),
    }


def _visual_invalid_substitutes(evidence: dict[str, Any]) -> list[str]:
    invalid: list[str] = []
    if "normalized_design_path" in evidence or "normalized_runtime_path" in evidence:
        invalid.append("normalized_json_alignment_only")
    if "comparison_report" in evidence:
        invalid.append("design_alignment_report_as_pixel_report")
    if "actual_diff_percent" in evidence or "verdict" in evidence:
        invalid.append("worker_declared_diff_without_receipt")

    return invalid


def _task_family_matches(task_id: str, family: str) -> bool:
    return task_id == family or task_id.startswith(f"{family}.")


def _visual_expected_scope(
    task: dict[str, Any],
    contract: dict[str, Any],
) -> tuple[str | None, str | None]:
    expected = dict(task.get("expected_evidence") or {})
    expected_feature = expected.get("feature_slug")
    if not isinstance(expected_feature, str) or not expected_feature:
        contract_feature = contract.get("feature")
        expected_feature = contract_feature if isinstance(contract_feature, str) else None
    expected_command = contract.get("command")
    expected_command = expected_command if isinstance(expected_command, str) else None
    return expected_feature, expected_command
