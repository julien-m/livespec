"""Validate distinct final convention scopes and execute fresh deterministic gates."""

from collections.abc import Mapping
from pathlib import Path

from .conventions_feature_scope import FeatureScopeError
from .conventions_receipt import ConventionsReceiptError, verify_conventions_receipt


def final_conventions_missing_items(
    task: Mapping[str, object],
    evidence: Mapping[str, object],
    contract: Mapping[str, object],
    project_root: Path | None,
) -> list[str]:
    """Check both final receipts and rerun current feature and whole-repo gates.

    Args:
        task: Immutable final task with scope metadata.
        evidence: Submitted feature and repo receipt paths.
        contract: Immutable contract supplying the fallback feature identity.
        project_root: Root confining receipts and verification inputs.
    Returns:
        Missing or invalid proof labels; empty only after current gates PASS.
    Side effects:
        Executes configured deterministic convention checks; writes no receipts.
    """
    if project_root is None:
        return ["project_root_for_receipt_verification"]
    feature = _expected_feature(task, contract)
    missing = _receipt_missing(evidence, "conventions_receipt_path", feature, project_root)
    missing.extend(
        _receipt_missing(evidence, "repo_conventions_receipt_path", "repo", project_root)
    )
    if missing:
        return missing
    return current_conventions_missing_items(project_root, feature)


def current_conventions_missing_items(project_root: Path, feature: str | None) -> list[str]:
    """Execute the same feature/repo paths as the CLI, including registry blockers.

    Args:
        project_root: Current project root.
        feature: Effective feature; None or repo means the whole repository.
    Returns:
        Failure labels for each current scope; historical PASS never overrides them.
    Side effects:
        Runs configured bounded linters and deterministic source checks.
    """
    # Deferred import breaks the CLI/receipt/goal consumer dependency cycle and
    # preserves CLI-only source-decision and ARS registry blockers in the rerun.
    from .cli_commands.conventions_cmd import _run_supervisor_verify

    scopes = (feature, None) if feature and feature != "repo" else (None,)
    missing: list[str] = []
    for scope in scopes:
        identity = scope or "repo"
        try:
            result = _run_supervisor_verify(project_root, scope)
        except (OSError, ValueError, FeatureScopeError) as exc:
            missing.append(f"conventions_current_valid:{identity}:{exc}")
            continue
        if result.verdict.value != "PASS":
            missing.append(f"conventions_current_verdict_pass:{identity}:{result.verdict.value}")
    return missing


def _expected_feature(task: Mapping[str, object], contract: Mapping[str, object]) -> str:
    expected = task.get("expected_evidence")
    if isinstance(expected, dict) and isinstance(expected.get("feature_slug"), str):
        return str(expected["feature_slug"])
    feature = contract.get("feature")
    return feature if isinstance(feature, str) and feature else "repo"


def _receipt_missing(
    evidence: Mapping[str, object], key: str, identity: str, project_root: Path
) -> list[str]:
    path = evidence.get(key)
    if not isinstance(path, str) or not path.strip():
        return [key]
    try:
        receipt = verify_conventions_receipt(
            Path(path), project_root=project_root, expected_feature_slug=identity
        )
    except (OSError, ConventionsReceiptError) as exc:
        return [f"{key}_valid:{exc}"]
    return [] if receipt.verdict == "PASS" else [f"{key}_verdict_pass"]
