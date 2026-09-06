"""Delegate the pre-review C20 guard to the installed Penflow authority."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .penflow_approval_files import PenflowApprovalError, load_object


# @spec FR-007: Validate canonical input before review
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-007
def validate_review_contract(project_root: Path, contract_path: Path) -> None:
    """Require valid C20 and explicit selectors without repairing reviewed inputs.

    Args:
        project_root: Caller-owned execution directory and filesystem boundary.
        contract_path: Immutable contract snapshot to be sent to the reviewer.

    Raises:
        PenflowApprovalError: Absent authority, invalid contract or changed input.
    """
    try:
        root = project_root.resolve(strict=True)
        original = contract_path.absolute()
        resolved = original.resolve(strict=True)
        resolved.relative_to(root)
        raw = resolved.read_bytes()
        executable = shutil.which("penflow")
        if executable is None:
            raise PenflowApprovalError("review_contract_penflow_cli_required")
        result = subprocess.run(
            [
                executable,
                "validate-flow-contract",
                str(resolved),
                "--require-test-ids",
                "--project",
                str(root),
                "--json",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            detail = ""
            try:
                rejected = load_object(result.stdout.encode("utf-8"))
                issues = rejected.get("issues", [])
                if isinstance(issues, list):
                    codes = [
                        item["code"]
                        for item in issues
                        if isinstance(item, dict) and isinstance(item.get("code"), str)
                    ]
                    detail = ": " + ", ".join(codes[:5]) if codes else ""
            except ValueError:
                # An older CLI may reject the required option without JSON.
                detail = ": compatible Penflow CLI and valid C20 required"
            raise PenflowApprovalError("review_contract_validation_failed" + detail)
        payload = load_object(result.stdout.encode("utf-8"))
        if payload.get("status") != "PASS" or payload.get("issues") != []:
            raise PenflowApprovalError("review_contract_nonpassing_response")
        if original.resolve(strict=True) != resolved or resolved.read_bytes() != raw:
            raise PenflowApprovalError("review_contract_changed_during_validation")
    except PenflowApprovalError:
        raise
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        raise PenflowApprovalError(f"review_contract_validation_unavailable: {exc}") from exc
