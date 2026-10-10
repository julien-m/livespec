"""Goal archive evidence responsibilities behind the public contract facade."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import goal_contracts as _contracts


# @spec FR-005: finalize.registry rejects all substitute evidence,
#   FR-006: verify_finalize_receipt wired into goal prove
#   — .specs/features/058-deterministic-finalization/spec.md#fr-005
def _validate_finalize_receipt_evidence(
    task: dict[str, Any],
    evidence: dict[str, Any],
    *,
    contract: dict[str, Any],
    project_root: Path | None,
) -> dict[str, Any]:
    missing: list[str] = []
    invalid: list[str] = []
    receipt_path = evidence.get("finalize_receipt_path")
    if not isinstance(receipt_path, str) or not receipt_path.strip():
        # Name each substitute so the rejection explains exactly which proxy
        # was offered instead of the receipt (AC-008).
        if evidence.get("output") or evidence.get("prose") or evidence.get("registry_updated"):
            invalid.append("prose_finalization_claim")
        if "exit_code" in evidence:
            invalid.append("exit_code_without_receipt")
        if "files" in evidence or "paths" in evidence or "file_list" in evidence:
            invalid.append("declared_file_list_without_receipt")
        missing.append("finalize_receipt_path")
    elif project_root is None:
        missing.append("project_root_for_receipt_verification")
    else:
        expected = dict(task.get("expected_evidence") or {})
        expected_feature = expected.get("feature_slug")
        if not isinstance(expected_feature, str) or not expected_feature:
            contract_feature = contract.get("feature")
            expected_feature = contract_feature if isinstance(contract_feature, str) else None
        expected_command = contract.get("command")
        expected_command = expected_command if isinstance(expected_command, str) else None
        try:
            receipt = _contracts.verify_finalize_receipt(
                Path(receipt_path),
                project_root=project_root,
                expected_feature_slug=expected_feature,
                expected_command=expected_command,
            )
        except (OSError, _contracts.FinalizeReceiptError) as exc:
            missing.append(f"finalize_receipt_valid:{exc}")
        else:
            if receipt.verdict != "PASS":
                missing.append("finalize_receipt_verdict_pass")
    accepted = not missing and not invalid
    return {
        "status": "ACCEPTED" if accepted else "REJECTED_NEEDS_ACTION",
        "accepted": accepted,
        "missing_evidence": missing,
        "invalid_substitutes": invalid,
        "required_actions": list(task["repair_if_missing"]),
    }


# @spec FR-003: Read-only prove validator for archive.run
#   — .specs/features/059-pipeline-verify-phase/spec.md#fr-003
def _validate_archive_run_evidence(
    task: dict[str, Any],
    evidence: dict[str, Any],
    *,
    contract: dict[str, Any],
    project_root: Path | None,
) -> dict[str, Any]:
    """Validate archive.run evidence against the on-disk run artifact.

    Read-only bootstrap (AC-005): the proof happens AFTER `livespec goal
    archive` ran, so this validator only loads the artifact from disk and
    never re-archives — a single archive per run stays canonical. Any
    artifact whose goal hash and command match the contract is accepted, not
    only the lexicographically latest one (EC-002).
    """
    missing: list[str] = []
    invalid: list[str] = []
    artifact_path_raw = evidence.get("run_artifact_path")
    if not isinstance(artifact_path_raw, str) or not artifact_path_raw.strip():
        # Name each offered substitute so the rejection explains exactly which
        # proxy was offered instead of the artifact path (AC-003).
        if evidence.get("output") or evidence.get("prose") or evidence.get("archived"):
            invalid.append("prose_archive_claim")
        if "exit_code" in evidence:
            invalid.append("exit_code_without_artifact")
        if _contracts._offers_tmpdir_contract_state_paths(evidence):
            invalid.append("tmpdir_contract_state_paths_without_artifact")
        missing.append("run_artifact_path")
    elif project_root is None:
        missing.append("project_root_for_artifact_verification")
    else:
        missing.extend(
            _contracts._archive_run_artifact_mismatches(
                artifact_path_raw,
                contract=contract,
                project_root=project_root,
            )
        )
    accepted = not missing and not invalid
    return {
        "status": "ACCEPTED" if accepted else "REJECTED_NEEDS_ACTION",
        "accepted": accepted,
        "missing_evidence": missing,
        "invalid_substitutes": invalid,
        "required_actions": list(task["repair_if_missing"]),
    }


__all__ = [
    "_archive_run_artifact_mismatches",
    "_offers_tmpdir_contract_state_paths",
    "_validate_archive_run_evidence",
    "_validate_finalize_receipt_evidence",
]


def _archive_run_artifact_mismatches(
    artifact_path_raw: str,
    *,
    contract: dict[str, Any],
    project_root: Path,
) -> list[str]:
    """Check containment, v2 load, and goal/command identity of the artifact.

    Returns:
        Named missing-evidence items (AC-004); empty when the artifact proves
        the archive.
    """
    missing: list[str] = []
    runs_root = (project_root / ".specs" / ".runs").resolve()
    submitted = Path(artifact_path_raw)
    resolved = (
        submitted.resolve() if submitted.is_absolute() else (project_root / submitted).resolve()
    )
    try:
        resolved.relative_to(runs_root)
    except ValueError:
        missing.append("run_artifact_under_specs_runs")
        return missing
    try:
        artifact = _contracts.load_run_artifact(resolved)
    except (OSError, _contracts.ArtifactMalformed) as exc:
        missing.append(f"run_artifact_valid:{exc}")
        return missing
    if artifact.get("goal_hash") != contract.get("goal_hash"):
        missing.append("run_artifact_goal_hash_match")
    if artifact.get("command") != contract.get("command"):
        missing.append("run_artifact_command_match")
    return missing


def _offers_tmpdir_contract_state_paths(evidence: Mapping[str, object]) -> bool:
    """Return True when the evidence offers $TMPDIR contract/state paths.

    Explicit contract/state keys are substitute evidence even when the value
    is not a TMPDIR path; string values containing the livespec-goals marker
    catch older payload shapes that only provided a path.
    """
    substitute_keys = {"contract_file", "state_file", "contract", "state"}
    if any(evidence.get(key) for key in substitute_keys):
        return True
    return any(
        isinstance(value, str) and _contracts.CHILD_GOAL_ARTIFACT_ROOT_MARKER in value
        for value in evidence.values()
    )
