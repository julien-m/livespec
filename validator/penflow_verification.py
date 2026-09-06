"""Revalidate Penflow certificates through the installed authoritative CLI."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal


class VerificationProfile(StrEnum):
    """Caller-selected certification stage; never inferred from a report."""

    DESIGN = "design"
    IMPLEMENTATION = "implementation"


@dataclass(frozen=True)
class PenflowVerification:
    """Transient result of current certificate revalidation."""

    status: Literal["PASS", "FAIL", "BLOCKED"]
    reason: str


@dataclass(frozen=True)
class _ValidationIdentity:
    project_root: str
    workspace: str
    report_path: str
    report_sha256: str
    build_manifest: dict[str, str] | None


def _validation_identity(
    project_root: Path,
    workspace: Path,
    build_manifest: Path | None,
) -> _ValidationIdentity:
    return _ValidationIdentity(
        str(project_root.resolve()),
        str(workspace.resolve()),
        str((workspace / "run-report.json").resolve()),
        hashlib.sha256((workspace / "run-report.json").read_bytes()).hexdigest(),
        {
            "path": str(build_manifest.resolve()),
            "sha256": hashlib.sha256(build_manifest.read_bytes()).hexdigest(),
        }
        if build_manifest is not None
        else None,
    )


# @spec FR-002, FR-003: C51 external authority
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-002
def verify_penflow_report(
    project_root: Path,
    workspace: Path,
    profile: VerificationProfile,
    build_manifest: Path | None,
) -> PenflowVerification:
    """Validate a current report using Penflow without writing project files.

    Args:
        project_root: Consumer boundary, distinct from its workspace directory.
        workspace: Selected canonical workspace containing run-report.json.
        profile: Required stage supplied by the caller.
        build_manifest: Independent runner input, mandatory for implementation.

    Returns:
        A certifying PASS or an actionable noncertifying result.
    """
    if profile is VerificationProfile.IMPLEMENTATION and build_manifest is None:
        return PenflowVerification("BLOCKED", "independent_build_manifest_required")
    report = workspace / "run-report.json"
    if not report.is_file():
        return PenflowVerification("BLOCKED", "verification_report_missing")
    effective_build = build_manifest if profile is VerificationProfile.IMPLEMENTATION else None
    try:
        identity = _validation_identity(project_root, workspace, effective_build)
    except (OSError, RuntimeError) as exc:
        return PenflowVerification("BLOCKED", f"verification_input_unreadable: {exc}")
    executable = shutil.which("penflow")
    if executable is None:
        return PenflowVerification("BLOCKED", "compatible_penflow_cli_required")
    arguments = [
        executable,
        "validate-report",
        identity.report_path,
        "--schema",
        "--required-profile",
        profile.value,
        "--project",
        identity.project_root,
        "--json",
    ]
    if identity.build_manifest is not None:
        arguments.extend(["--build-manifest", identity.build_manifest["path"]])
    # C51 reads current bindings and returns a versioned JSON envelope; no shell or retries.
    try:
        completed = subprocess.run(
            arguments,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return PenflowVerification("BLOCKED", "penflow_validation_timeout")
    except OSError as exc:
        return PenflowVerification("BLOCKED", f"penflow_validation_unavailable: {exc}")
    except UnicodeError:
        return PenflowVerification("BLOCKED", "penflow_validation_invalid_encoding")
    # Bind the response to requested bytes, detecting changes during external validation.
    try:
        if identity != _validation_identity(project_root, workspace, effective_build):
            return PenflowVerification("BLOCKED", "verification_inputs_changed")
    except (OSError, RuntimeError) as exc:
        return PenflowVerification("BLOCKED", f"verification_input_unreadable: {exc}")
    return _verification_response(completed, profile, identity)


def _verification_response(
    completed: subprocess.CompletedProcess[str],
    profile: VerificationProfile,
    identity: _ValidationIdentity,
) -> PenflowVerification:
    try:
        raw: object = json.loads(completed.stdout)
    except (json.JSONDecodeError, UnicodeError):
        return PenflowVerification("BLOCKED", "penflow_validation_invalid_json")
    if not isinstance(raw, dict):
        return PenflowVerification("BLOCKED", "penflow_validation_invalid_envelope")
    if (
        raw.get("kind") != "penflow-verification-validation"
        or type(raw.get("version")) is not int
        or raw.get("version") != 1
        or raw.get("required_profile") != profile.value
        or not isinstance(raw.get("issues"), list)
    ):
        return PenflowVerification("BLOCKED", "penflow_validation_incompatible_envelope")
    if raw.get("status") == "FAIL":
        return PenflowVerification("FAIL", "penflow_rejected_verification_report")
    if (
        completed.returncode != 0
        or raw.get("status") != "PASS"
        or raw.get("profile") != profile.value
        or raw.get("issues") != []
        or raw.get("report_sha256") != identity.report_sha256
        or raw.get("scope")
        != {
            "project_root": identity.project_root,
            "workspace": identity.workspace,
        }
        or "build_manifest" not in raw
        or raw.get("build_manifest") != identity.build_manifest
    ):
        return PenflowVerification("BLOCKED", "penflow_validation_noncertifying_response")
    return PenflowVerification("PASS", "current_penflow_report_validated")
