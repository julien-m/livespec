"""Goal generic evidence responsibilities behind the public contract facade."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from . import goal_contracts as _contracts

__all__ = [
    "_convention_evidence_satisfied",
    "_conventions_receipt_missing_items",
    "_manifest_or_boolean_evidence",
    "_required_evidence_satisfied",
    "_string_set_evidence",
    "_validate_generic_evidence",
]


def _validate_generic_evidence(
    task: dict[str, Any],
    evidence: dict[str, Any],
    *,
    contract: dict[str, Any],
    project_root: Path | None,
) -> dict[str, Any]:
    missing = _contracts.typed_evidence_missing(
        task, evidence, contract=contract, project_root=project_root
    )
    if not evidence:
        missing.extend(task["required_evidence"])
    for required in cast(list[object], task.get("required_evidence") or []):
        if not isinstance(required, str):
            continue
        if required in {
            "execution_receipt_path",
            "review_receipt_path",
            "acceptance_review_receipt_path",
            "spec_review_receipt_path",
        }:
            continue  # Independently verified by the versioned policy above.
        if required == "conventions_receipt_path":
            missing.extend(
                _contracts._conventions_receipt_missing_items(
                    task,
                    evidence,
                    contract=contract,
                    project_root=project_root,
                )
            )
            continue
        if required.startswith("convention_") or required == "conventions_applied_to_output":
            satisfied = _contracts._convention_evidence_satisfied(task, required, evidence)
        else:
            satisfied = _contracts._required_evidence_satisfied(required, evidence, project_root)
        if not satisfied:
            missing.append(required)
    accepted = not missing
    return {
        "status": "ACCEPTED" if accepted else "REJECTED_NEEDS_ACTION",
        "accepted": accepted,
        "missing_evidence": missing,
        "invalid_substitutes": [],
        "required_actions": list(task["repair_if_missing"]),
    }


def _conventions_receipt_missing_items(
    task: Mapping[str, object],
    evidence: Mapping[str, object],
    *,
    contract: Mapping[str, object],
    project_root: Path | None,
) -> list[str]:
    """Validate conventions receipt evidence and return missing proof labels."""
    receipt_path = evidence.get("conventions_receipt_path")
    if not isinstance(receipt_path, str) or not receipt_path.strip():
        return ["conventions_receipt_path"]
    if project_root is None:
        return ["project_root_for_receipt_verification"]
    submitted = Path(receipt_path)
    resolved = (
        submitted.resolve() if submitted.is_absolute() else (project_root / submitted).resolve()
    )
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError:
        return [f"conventions_receipt_valid:path_outside_project:{receipt_path}"]
    expected = task.get("expected_evidence")
    expected_feature = None
    if isinstance(expected, dict) and isinstance(expected.get("feature_slug"), str):
        expected_feature = str(expected["feature_slug"])
    elif isinstance(contract.get("feature"), str):
        expected_feature = str(contract["feature"])
    try:
        receipt = _contracts.verify_conventions_receipt(
            resolved,
            project_root=project_root,
            expected_feature_slug=expected_feature,
        )
    except (OSError, _contracts.ConventionsReceiptError) as exc:
        return [f"conventions_receipt_valid:{exc}"]
    if receipt.verdict != "PASS":
        return ["conventions_receipt_verdict_pass"]
    return []


# @spec FR-003: Validate convention evidence
#   — .specs/features/053-goal-tasks-replay-required-conventions-per-step/spec.md#fr-003
def _convention_evidence_satisfied(
    task: Mapping[str, object],
    required: str,
    evidence: Mapping[str, object],
) -> bool:
    required_conventions = task.get("required_conventions")
    if not isinstance(required_conventions, dict):
        return True
    required_domains = {
        str(domain)
        for domain in cast(list[object], required_conventions.get("domains") or [])
        if isinstance(domain, str)
    }
    required_sources = {
        str(source)
        for source in cast(list[object], required_conventions.get("source_paths") or [])
        if isinstance(source, str)
    }
    if required == "convention_domains_recorded":
        provided_domains = _contracts._string_set_evidence(
            evidence,
            ("convention_domains", "convention_domains_recorded"),
        )
        return bool(required_domains) and required_domains.issubset(provided_domains)
    if required == "convention_sources_read":
        provided_sources = _contracts._string_set_evidence(
            evidence,
            ("convention_sources", "convention_source_paths", "convention_sources_read"),
        )
        return bool(required_sources) and required_sources.issubset(provided_sources)
    if required == "conventions_applied_to_output":
        return evidence.get(required) is True
    return False


def _string_set_evidence(evidence: Mapping[str, object], keys: tuple[str, ...]) -> set[str]:
    """Collect string or list-of-string evidence values for convention checks."""
    values: set[str] = set()
    for key in keys:
        value = evidence.get(key)
        # Evidence may be one string or a list; other JSON values are invalid proof.
        if isinstance(value, str) and value.strip():
            values.add(value.strip())
        elif isinstance(value, list):
            values.update(item.strip() for item in value if isinstance(item, str) and item.strip())
    return values


def _required_evidence_satisfied(
    required: str,
    evidence: dict[str, Any],
    project_root: Path | None,
) -> bool:
    if required == "observable_output_or_artifact":
        return bool(evidence.get("output")) or _contracts._any_evidence_path_exists(
            evidence, ("artifact", "path", "paths", "files"), project_root
        )
    if required == "success_criteria_met":
        return evidence.get("success_criteria_met") is True
    if required == "child_goal_hash_recorded":
        return _contracts._nonempty_str(
            evidence.get("child_goal_hash")
        ) or _contracts._nonempty_str(evidence.get(required))
    if required in {"child_contract_file_exists", "child_state_file_exists"}:
        return _child_file_evidence(required, evidence)
    if required == "child_final_status_recorded":
        value = evidence.get("child_final_status", evidence.get(required))
        return isinstance(value, str) and value.lower() in {"complete", "completed", "pass"}
    if required == "command_exit_code_recorded":
        return evidence.get("exit_code", evidence.get(required)) == 0
    if required == "json_verdict_recorded":
        value = evidence.get("json_verdict", evidence.get("verdict"))
        return isinstance(value, str) and value.upper() == "PASS"
    if required == "missing_artifacts_list_recorded":
        value = evidence.get("missing_artifacts", evidence.get(required))
        return isinstance(value, list) and not value
    if required == "penflow_artifact_path_exists":
        return _contracts._any_evidence_path_exists(
            evidence, (required, "penflow_artifact_path", "report_path"), project_root
        )
    if required == "penflow_status_or_report_recorded":
        status = evidence.get("penflow_status", evidence.get("status"))
        if isinstance(status, str) and status.upper() in {"PASS", "OK", "SUCCESS", "COMPLETE"}:
            return True
        return _contracts._any_evidence_path_exists(evidence, ("report_path",), project_root)
    if required == "artifact_path_exists":
        return _contracts._any_evidence_path_exists(
            evidence,
            (required, "artifact", "artifact_path", "path", "paths", "files"),
            project_root,
        )
    return _contracts._manifest_or_boolean_evidence(required, evidence)


def _manifest_or_boolean_evidence(required: str, evidence: dict[str, Any]) -> bool:
    if required == "hash_or_manifest_status_recorded":
        digest = evidence.get("sha256", evidence.get("hash"))
        if isinstance(digest, str) and re.fullmatch(r"[a-fA-F0-9]{64}", digest):
            return True
        status = evidence.get("manifest_status")
        return isinstance(status, str) and status.upper() in {"PASS", "OK", "VALID"}
    return evidence.get(required) is True


def _child_file_evidence(required: str, evidence: dict[str, Any]) -> bool:
    if required == "child_contract_file_exists":
        return _contracts._child_goal_artifact_exists(
            evidence,
            (required, "child_contract_file", "contract_file"),
            ".contract.json",
            "contract",
        )
    if required == "child_state_file_exists":
        return _contracts._child_goal_artifact_exists(
            evidence,
            (required, "child_state_file", "state_file"),
            ".state.json",
            "state",
        )
    return False
