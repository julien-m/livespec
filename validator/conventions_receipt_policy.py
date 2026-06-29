# @spec FR-014: mode-aware receipt consumers
#   .specs/features/072-conventions-ast-rule-engine/spec.md#fr-014

"""Mode-aware policy for consumers of conventions receipts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .conventions_gates import ConventionsGatesV2, gates_path, load_conventions_gates
from .conventions_receipt import ConventionsReceiptError, verify_conventions_receipt

ReceiptPolicyState = Literal["unchanged", "observe_warning", "pass", "block"]
ReceiptPolicySeverity = Literal["INFO", "WARNING", "ERROR"]


@dataclass(frozen=True)
class ConventionsReceiptPolicy:
    """Decision returned to commands that consume AST conventions receipts."""

    state: ReceiptPolicyState
    blocks: bool
    severity: ReceiptPolicySeverity
    reason: str


def evaluate_conventions_receipt_policy(
    project_root: Path,
    *,
    command: str,
    expected_feature_slug: str | None = None,
) -> ConventionsReceiptPolicy:
    """Evaluate how the latest conventions receipt affects a command."""
    mode = _ast_mode(project_root)
    if mode is None or mode == "off":
        return ConventionsReceiptPolicy("unchanged", False, "INFO", "AST rules are disabled")
    latest = _latest_conventions_receipt(
        project_root,
        mode=mode,
        expected_feature_slug=expected_feature_slug,
    )
    if latest is None:
        return _missing_receipt_policy(command, mode)
    try:
        receipt = verify_conventions_receipt(
            latest,
            project_root=project_root,
            expected_feature_slug=expected_feature_slug,
        )
    except (OSError, ConventionsReceiptError, json.JSONDecodeError) as exc:
        return _unverified_receipt_policy(command, mode, exc)
    if mode == "observe":
        return _observe_policy(command, receipt.ast_would_fail_count, receipt.ast_backend)
    if receipt.verdict != "PASS":
        return ConventionsReceiptPolicy(
            "block",
            True,
            "ERROR",
            f"{command}: conventions AST enforce receipt is {receipt.verdict}",
        )
    return ConventionsReceiptPolicy(
        "pass",
        False,
        "INFO",
        f"{command}: conventions AST enforce receipt passed",
    )


def _missing_receipt_policy(command: str, mode: str) -> ConventionsReceiptPolicy:
    if mode == "observe":
        return ConventionsReceiptPolicy(
            "observe_warning",
            False,
            "WARNING",
            f"{command}: conventions AST observe receipt missing",
        )
    return ConventionsReceiptPolicy(
        "block",
        True,
        "ERROR",
        f"{command}: conventions AST enforce receipt missing",
    )


def _unverified_receipt_policy(command: str, mode: str, exc: Exception) -> ConventionsReceiptPolicy:
    if mode == "observe":
        return ConventionsReceiptPolicy(
            "observe_warning",
            False,
            "WARNING",
            f"{command}: conventions AST observe receipt unverified: {exc}",
        )
    return ConventionsReceiptPolicy(
        "block",
        True,
        "ERROR",
        f"{command}: conventions AST enforce receipt unverified: {exc}",
    )


def _ast_mode(project_root: Path) -> str | None:
    try:
        gates = load_conventions_gates(gates_path(project_root))
    except (OSError, ValueError):
        return None
    if not isinstance(gates, ConventionsGatesV2):
        return None
    return gates.ast_rules.mode


def _latest_conventions_receipt(
    project_root: Path,
    *,
    mode: str,
    expected_feature_slug: str | None,
) -> Path | None:
    runs_root = project_root / ".specs" / "conventions" / "runs"
    if not runs_root.is_dir():
        return None
    receipts = [
        path
        for path in runs_root.glob("*/receipt.json")
        if _receipt_matches_policy(path, project_root, mode, expected_feature_slug)
    ]
    if not receipts:
        return None
    return max(receipts, key=lambda path: (path.stat().st_mtime_ns, path.as_posix()))


def _receipt_matches_policy(
    receipt_path: Path,
    project_root: Path,
    mode: str,
    expected_feature_slug: str | None,
) -> bool:
    try:
        receipt = verify_conventions_receipt(
            receipt_path,
            project_root=project_root,
            expected_feature_slug=expected_feature_slug,
        )
    except (OSError, ConventionsReceiptError, json.JSONDecodeError):
        return False
    return receipt.ast_mode == mode


def _observe_policy(
    command: str,
    would_fail_count: int | None,
    ast_backend: dict[str, object] | None,
) -> ConventionsReceiptPolicy:
    backend_status = str((ast_backend or {}).get("status", "unknown"))
    if backend_status != "available":
        return ConventionsReceiptPolicy(
            "observe_warning",
            False,
            "WARNING",
            f"{command}: conventions AST observe backend is {backend_status}",
        )
    count = would_fail_count or 0
    if count > 0:
        return ConventionsReceiptPolicy(
            "observe_warning",
            False,
            "WARNING",
            f"{command}: conventions AST observe found {count} would-fail match(es)",
        )
    return ConventionsReceiptPolicy(
        "pass",
        False,
        "INFO",
        f"{command}: conventions AST observe receipt has no findings",
    )


__all__ = ["ConventionsReceiptPolicy", "evaluate_conventions_receipt_policy"]
