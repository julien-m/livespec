# LiveSpec traceability anchors
# @spec(FR-001)
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-006)
# @spec(FR-009)

"""Deterministic end-of-command registry finalization (Feature 058).

Public API home for ``livespec finalize`` (FR-009): apply/verify
orchestration plus re-exported receipt primitives. Receipt and registry
helpers live in :mod:`validator.finalize_receipt` and
:mod:`validator.finalize_registry` to honor the 300-line constitution cap;
always import from this module.

Naming note (Edge Case 9): Feature 048 "run finalization" verifies
RunArtifacts against expectations.md; this module is *registry*
finalization (changelog/README/status writes) — a distinct surface.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .coherence.rule_engine import run_coherence
from .coherence.violation import Severity, Violation
from .finalize_readme import build_readme

# @spec FR-009: finalize.py is the public logic home
#   — .specs/features/058-deterministic-finalization/spec.md#fr-009
from .finalize_receipt import (
    FINALIZE_ORACLE_NAME,
    FINALIZE_ORACLE_VERSION,
    FINALIZE_RECEIPT_SCHEMA_VERSION,
    MARKER_TEMPLATE,
    FinalizeError,
    FinalizeFileEntry,
    FinalizeOutcome,
    FinalizeReceipt,
    FinalizeReceiptError,
    FinalizeVerdict,
    FinalizeViolation,
    compute_hash8,
    compute_payload_hash,
    verify_finalize_receipt,
    write_receipt,
)
from .finalize_registry import (
    APPLY_TARGET_ORDER,
    RegistryTarget,
    build_feature_changelog,
    build_global_changelog,
    build_spec_status,
    is_target_marked,
    render_marker,
    target_path,
)
from .locks import (
    LockRetryPolicy,
    WriteHashMismatchError,
    acquire_lock,
    write_with_hash_check,
)

# Coherence rules re-evaluated by `finalize verify`, scoped to the feature
# (FR-004): roadmap/features (R1), README sync (R4), changelog refs (R6).
VERIFY_COHERENCE_RULE_IDS: tuple[str, ...] = ("R1", "R4", "R6")

# Marker presence is required on the three always-written registry targets.
# spec_status is exempt: `--status` is optional by design (plan.md Step 6),
# so a command may legitimately finalize without stamping spec.md.
_MARKER_CHECKED_TARGETS: tuple[RegistryTarget, ...] = (
    "feature_changelog",
    "global_changelog",
    "readme",
)


@dataclass(frozen=True)
class ApplyRequest:
    """Structured, date-free input for one ``finalize apply`` run.

    Bodies MUST NOT contain the entry date: dates are rendered at write time
    so the hash8 identity stays stable across days (FR-002).

    Attributes:
        feature_slug: Feature directory slug (``NNN-name``).
        command: Finalizing LiveSpec command (e.g. ``spec-specify``).
        status: New spec status, or ``None`` to skip the spec_status target.
        entry_body: Feature changelog entry body (date-free).
        global_summary: Global changelog summary line (date-free).
        run_id: Run identifier used for the receipt directory.
    """

    feature_slug: str
    command: str
    status: str | None
    entry_body: str
    global_summary: str
    run_id: str

    def canonical_payload(self) -> dict[str, object]:
        """Return the canonical hash8 payload (volatile fields excluded).

        ``status`` is omitted (not nulled) when absent so the identity of a
        no-status apply stays deterministic and distinct (plan.md Step 6).
        """
        payload: dict[str, object] = {
            "feature_slug": self.feature_slug,
            "command": self.command,
            "entry_body": self.entry_body,
            "global_summary": self.global_summary,
        }
        if self.status is not None:
            payload["status"] = self.status
        return payload

    def payload_hash(self) -> str:
        """Return the full sha256 of the canonical payload."""
        return compute_payload_hash(self.canonical_payload())

    def hash8(self) -> str:
        """Return the 8-hex marker identity for this request."""
        return compute_hash8(self.canonical_payload())


def write_finalize_receipt(
    *,
    project_root: Path,
    request: ApplyRequest,
    outcome: FinalizeOutcome,
    verdict: FinalizeVerdict,
    files: list[Path],
    violations: list[FinalizeViolation],
) -> Path:
    """Write a finalize receipt for ``request`` and return its path.

    See :func:`validator.finalize_receipt.write_receipt` for field semantics.
    """
    return write_receipt(
        project_root=project_root,
        feature_slug=request.feature_slug,
        command=request.command,
        run_id=request.run_id,
        payload_hash=request.payload_hash(),
        outcome=outcome,
        verdict=verdict,
        files=files,
        violations=violations,
    )


@dataclass(frozen=True)
class FinalizeApplyResult:
    """Outcome of one ``finalize apply`` run."""

    outcome: FinalizeOutcome
    receipt_path: Path
    written: tuple[RegistryTarget, ...]
    skipped: tuple[RegistryTarget, ...]


@dataclass(frozen=True)
class FinalizeVerifyResult:
    """Outcome of one read-only ``finalize verify`` run."""

    verdict: FinalizeVerdict
    receipt_path: Path
    violations: tuple[FinalizeViolation, ...]


def apply_finalization(
    project_root: Path,
    request: ApplyRequest,
    *,
    retry_policy: LockRetryPolicy | None = None,
    today: date | None = None,
) -> FinalizeApplyResult:
    """Apply all end-of-command registry updates atomically and idempotently.

    @spec FR-001: atomic lock-guarded four-target apply
    — .specs/features/058-deterministic-finalization/spec.md#fr-001

    Args:
        project_root: Project root containing ``.specs/``.
        request: Structured, date-free update payload.
        retry_policy: Opt-in lock retry (``--retry``, FR-007).
        today: Injectable date for deterministic tests (defaults to today).

    Returns:
        :class:`FinalizeApplyResult` with the receipt path and written targets.

    Raises:
        FinalizeError: ``state_invalid`` on hash mismatch (receipt attached)
            or broken registry anchors.
        LockAcquisitionError: Lock timeout — no registry file modified.
    """
    apply_date = today or date.today()
    specs_root = project_root / ".specs"
    feature_dir = specs_root / "features" / request.feature_slug
    if not feature_dir.is_dir():
        raise FinalizeError(
            f"feature directory missing: {feature_dir}",
            subtype="state_invalid",
        )
    hash8 = request.hash8()
    targets = _active_targets(request)
    marker = render_marker(request.command, apply_date, hash8)

    def _pending() -> list[RegistryTarget]:
        return [
            target
            for target in targets
            if not is_target_marked(
                target_path(project_root, target, request.feature_slug),
                request.command,
                hash8,
            )
        ]

    # @spec FR-002: marker-based idempotence + zero-write re-run
    # — .specs/features/058-deterministic-finalization/spec.md#fr-002
    if not _pending():
        receipt_path = _write_apply_receipt(
            project_root, request, "already_finalized", "PASS", targets, []
        )
        return FinalizeApplyResult("already_finalized", receipt_path, (), targets)

    written: list[RegistryTarget] = []
    try:
        with acquire_lock(specs_root, retry_policy=retry_policy):
            # Order matters: the pre-scan above is an optimization only; this
            # in-lock re-scan is the correctness check against concurrent
            # appliers racing on the same feature (Edge Case 7).
            pending = _pending()
            skipped: tuple[RegistryTarget, ...] = tuple(
                target for target in targets if target not in pending
            )
            for target in pending:
                path = target_path(project_root, target, request.feature_slug)
                if target == "global_changelog":
                    content, archived = build_global_changelog(path, request, apply_date, marker)
                    # Order matters: archives are persisted before the trimmed
                    # changelog so a crash between the two writes never loses
                    # rotated entries (FR-010).
                    _persist_changelog_archives(specs_root, archived)
                else:
                    content = _build_target_content(
                        project_root, target, request, apply_date, marker
                    )
                write_with_hash_check(path, content)
                written.append(target)
    except WriteHashMismatchError as exc:
        # @spec FR-008: state_invalid surfacing with partial receipt
        # — .specs/features/058-deterministic-finalization/spec.md#fr-008
        receipt_path = _write_apply_receipt(
            project_root,
            request,
            "BLOCKED",
            "BLOCKED",
            written,
            [FinalizeViolation(rule_id="write.hash_mismatch", message=str(exc))],
        )
        raise FinalizeError(
            f"post-write hash mismatch: {exc}",
            subtype="state_invalid",
            receipt_path=receipt_path,
        ) from exc
    receipt_path = _write_apply_receipt(project_root, request, "applied", "PASS", targets, [])
    return FinalizeApplyResult("applied", receipt_path, tuple(written), skipped)


def verify_finalization(
    project_root: Path,
    feature_slug: str,
    *,
    expected_command: str | None = None,
    run_id: str,
) -> FinalizeVerifyResult:
    """Re-check registry coherence for one feature, strictly read-only.

    @spec FR-004: read-only R1/R4/R6 re-evaluation scoped to the feature
    — .specs/features/058-deterministic-finalization/spec.md#fr-004

    Args:
        project_root: Project root containing ``.specs/``.
        feature_slug: Feature whose registry coherence is re-checked.
        expected_command: When given, each always-written registry target
            must carry a finalize marker for this command (AC-006).
        run_id: Run identifier for the receipt directory.

    Returns:
        :class:`FinalizeVerifyResult` with the verdict, receipt path, and
        the violated rule IDs on FAIL.
    """
    specs_root = project_root / ".specs"
    # no_suppress: the suppress-if-creating grace window must not hide drift
    # from the verifier — a freshly edited spec is exactly when drift appears.
    coherence = run_coherence(
        specs_root,
        rule_ids=list(VERIFY_COHERENCE_RULE_IDS),
        no_suppress=True,
    )
    violations = [
        FinalizeViolation(rule_id=violation.rule_id, message=violation.message)
        for violation in coherence.violations
        if violation.severity is not Severity.INFO
        and _violation_concerns_feature(violation, feature_slug)
    ]
    if expected_command is not None:
        violations.extend(_missing_marker_violations(project_root, feature_slug, expected_command))
    checked_files = [
        target_path(project_root, target, feature_slug)
        for target in APPLY_TARGET_ORDER
        if target_path(project_root, target, feature_slug).is_file()
    ]
    verdict: FinalizeVerdict = "PASS" if not violations else "FAIL"
    receipt_path = write_receipt(
        project_root=project_root,
        feature_slug=feature_slug,
        command=expected_command or "verify",
        run_id=run_id,
        payload_hash=compute_payload_hash(
            {
                "feature_slug": feature_slug,
                "command": expected_command or "verify",
                "mode": "verify",
            }
        ),
        outcome="verified",
        verdict=verdict,
        files=checked_files,
        violations=violations,
    )
    return FinalizeVerifyResult(verdict, receipt_path, tuple(violations))


def _active_targets(request: ApplyRequest) -> tuple[RegistryTarget, ...]:
    if request.status is None:
        # `--status` omitted: the spec_status target is skipped by design so
        # commands that do not own the status (e.g. checks) can finalize.
        return tuple(target for target in APPLY_TARGET_ORDER if target != "spec_status")
    return APPLY_TARGET_ORDER


def _build_target_content(
    project_root: Path,
    target: RegistryTarget,
    request: ApplyRequest,
    apply_date: date,
    marker: str,
) -> str:
    path = target_path(project_root, target, request.feature_slug)
    if target == "feature_changelog":
        return build_feature_changelog(path, request, apply_date, marker)
    if target == "readme":
        # Read the global changelog fresh from disk: the apply order writes it
        # before the README so Recent Activity includes this run's entry.
        global_path = target_path(project_root, "global_changelog", request.feature_slug)
        global_content = global_path.read_text(encoding="utf-8") if global_path.is_file() else ""
        return build_readme(
            path, request, apply_date, marker, global_content, project_root / ".specs"
        )
    return build_spec_status(path, request, marker, apply_date)


def _persist_changelog_archives(specs_root: Path, archived: dict[int, str]) -> None:
    """Append rotated previous-year entry blocks to their archive files."""
    for year, block in sorted(archived.items()):
        archive_path = specs_root / "archive" / f"changelog-{year}.md"
        if archive_path.is_file():
            existing = archive_path.read_text(encoding="utf-8").rstrip() + "\n\n"
        else:
            existing = f"# Changelog {year}\n\n"
        write_with_hash_check(archive_path, existing + block)


def _missing_marker_violations(
    project_root: Path,
    feature_slug: str,
    expected_command: str,
) -> list[FinalizeViolation]:
    command_marker = re.compile(rf"<!-- finalize:{re.escape(expected_command)}:")
    violations: list[FinalizeViolation] = []
    for target in _MARKER_CHECKED_TARGETS:
        path = target_path(project_root, target, feature_slug)
        if not path.is_file() or not command_marker.search(path.read_text(encoding="utf-8")):
            violations.append(
                FinalizeViolation(
                    rule_id="marker.missing",
                    message=f"{path} carries no finalize marker for {expected_command}",
                )
            )
    return violations


def _violation_concerns_feature(violation: Violation, feature_slug: str) -> bool:
    # Scoping strategy (plan.md Step 5): match structured context keys first
    # (dir_name/feature_dir/ref carry the feature directory in R1/R4/R6),
    # then fall back to a message substring for indirectly phrased rules.
    for key in ("dir_name", "feature_dir", "ref"):
        value = violation.context.get(key)
        if isinstance(value, str) and value == feature_slug:
            return True
    return feature_slug in violation.message


def _write_apply_receipt(
    project_root: Path,
    request: ApplyRequest,
    outcome: FinalizeOutcome,
    verdict: FinalizeVerdict,
    targets: tuple[RegistryTarget, ...] | list[RegistryTarget],
    violations: list[FinalizeViolation],
) -> Path:
    files = [
        target_path(project_root, target, request.feature_slug)
        for target in targets
        if target_path(project_root, target, request.feature_slug).is_file()
    ]
    return write_receipt(
        project_root=project_root,
        feature_slug=request.feature_slug,
        command=request.command,
        run_id=request.run_id,
        payload_hash=request.payload_hash(),
        outcome=outcome,
        verdict=verdict,
        files=files,
        violations=violations,
    )


__all__ = [
    "FINALIZE_ORACLE_NAME",
    "FINALIZE_ORACLE_VERSION",
    "FINALIZE_RECEIPT_SCHEMA_VERSION",
    "MARKER_TEMPLATE",
    "VERIFY_COHERENCE_RULE_IDS",
    "ApplyRequest",
    "FinalizeApplyResult",
    "FinalizeError",
    "FinalizeFileEntry",
    "FinalizeOutcome",
    "FinalizeReceipt",
    "FinalizeReceiptError",
    "FinalizeVerdict",
    "FinalizeVerifyResult",
    "FinalizeViolation",
    "apply_finalization",
    "compute_hash8",
    "compute_payload_hash",
    "verify_finalization",
    "verify_finalize_receipt",
    "write_finalize_receipt",
]
