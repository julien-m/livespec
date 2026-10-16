"""Existing test command adapters for independent mapping review and execution (078 FR-010)."""

from __future__ import annotations

import json
import os
import shlex
import tempfile
from pathlib import Path
from typing import Literal

import typer

from validator.execution_capture import capture_execution
from validator.execution_evidence import (
    EvidenceVerification,
    verify_execution_observation,
    verify_execution_receipt,
)
from validator.execution_mapping import (
    AcceptanceMapping,
    ingest_mapping_review,
    prepare_mapping_review,
)
from validator.execution_mapping_anchors import derived_mapping
from validator.semantic.review_contract import REVIEW_SCHEMA

from .review_io import NativeReviewInput


def execution_io(
    root: Path,
    feature: str | None,
    *,
    command: str | None,
    mapping_path: Path | None,
    prepare: bool,
    ingest: Path | None,
    adapter: str,
    derive: bool = False,
    observation: Literal["passed", "red"] | None = None,
) -> None:
    """Expose mapping derivation, reviewer preparation/ingestion and certified capture."""
    # @spec FR-001: Explicit observations without AC mapping
    # — .specs/features/096-node-vitest-execution/spec.md#fr-001
    # @spec FR-005: Preserve strict acceptance beside observation
    # — .specs/features/096-node-vitest-execution/spec.md#fr-005
    if observation is not None:
        _observe(
            root, feature, command, mapping_path, prepare, ingest, adapter, derive, observation
        )
    if not feature or mapping_path is None:
        raise ValueError("execution_feature_and_acceptance_mapping_required")
    if derive and (root / mapping_path).is_symlink():
        raise ValueError("derive_mapping_refuses_a_linked_destination")
    mapping_path = (root / mapping_path).resolve()
    mapping_path.relative_to(root)
    if derive:
        _derive(root, feature, mapping_path)
    anchored = (
        mapping_path.is_file()
        and AcceptanceMapping.model_validate_json(mapping_path.read_bytes()).derivation == "anchors"
    )
    if anchored and (prepare or ingest):
        raise ValueError("anchored_mapping_needs_no_review")
    if anchored:
        _capture(root, feature, command, mapping_path, adapter)
    prepared = prepare_mapping_review(root, feature, mapping_path)
    if prepare:
        typer.echo(
            json.dumps({"prepared": prepared.model_dump(), "response_schema": REVIEW_SCHEMA})
        )
        raise typer.Exit(0 if prepared.complete else 1)
    if ingest:
        raw = NativeReviewInput.model_validate_json(ingest.read_text(encoding="utf-8"))
        mapping = AcceptanceMapping.model_validate_json(mapping_path.read_text(encoding="utf-8"))
        receipt_path = (root / mapping.review_receipt_path).resolve()
        receipt_path.relative_to(root)
        receipt = ingest_mapping_review(prepared, raw.raw_results, receipt_path, raw.synthesis)
        typer.echo(json.dumps({"receipt_path": str(receipt_path), **receipt.model_dump()}))
        raise typer.Exit(0 if receipt.complete and receipt.ready else 1)
    _capture(root, feature, command, mapping_path, adapter)


def _observe(
    root: Path,
    feature: str | None,
    command: str | None,
    mapping_path: Path | None,
    prepare: bool,
    ingest: Path | None,
    adapter: str,
    derive: bool,
    observation: Literal["passed", "red"],
) -> None:
    """Validate observation purpose before any mapping read and capture without certification."""
    from .operation_options import check_execution_options

    check_execution_options(
        feature=feature,
        command=command,
        mapping=mapping_path,
        prepare=prepare,
        ingest=ingest,
        adapter=adapter,
        mutation=False,
        no_coverage=False,
        debug=False,
        derive=derive,
        observation=observation,
    )
    if feature:
        # Observation must bypass mapping reads and independent acceptance review entirely.
        _capture(root, feature, command, None, adapter, observation)


def _derive(root: Path, feature: str, mapping_path: Path) -> None:
    """Write the anchor-derived mapping only when no blocking issue remains (087 FR-004)."""
    if mapping_path.exists() or mapping_path.is_symlink():
        try:
            AcceptanceMapping.model_validate_json(mapping_path.read_bytes())
        except (OSError, ValueError) as exc:
            raise ValueError("derive_mapping_refuses_to_overwrite_a_non_mapping_file") from exc
    mapping, derivation = derived_mapping(root, feature)
    if mapping is not None:
        _publish(mapping_path, mapping.model_dump_json(indent=2) + "\n")
    payload = {
        "feature": feature,
        "mapping_path": mapping_path.relative_to(root).as_posix() if mapping else None,
        "bindings": len(derivation.bindings),
        "acceptance": sorted({item.requirement_id for item in derivation.bindings}),
        "issues": [issue.to_json() for issue in derivation.issues],
    }
    typer.echo(json.dumps(payload))
    raise typer.Exit(0 if mapping is not None else 1)


def _publish(path: Path, text: str) -> None:
    """Atomic write that never follows a link at the destination."""
    if path.is_symlink():
        raise ValueError("derive_mapping_refuses_a_linked_destination")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".mapping-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _capture(
    root: Path,
    feature: str,
    command: str | None,
    mapping_path: Path | None,
    adapter: str,
    observation: Literal["passed", "red"] | None = None,
) -> None:
    if not command:
        raise ValueError("execution_command_required")
    capture = capture_execution(
        shlex.split(command),
        project_root=root,
        feature=feature,
        adapter=adapter,
        env=dict(os.environ),
        acceptance_mapping=mapping_path.relative_to(root).as_posix() if mapping_path else None,
    )
    if capture.receipt_path and observation is not None:
        result = verify_execution_observation(
            Path(capture.receipt_path), root, feature, observation
        )
    else:
        result = (
            verify_execution_receipt(Path(capture.receipt_path), root, feature)
            if capture.receipt_path
            else EvidenceVerification(
                valid=False, certified_acs=[], gaps=capture.gaps or ["No fresh execution receipt"]
            )
        )
    typer.echo(json.dumps({"execution_receipt_path": capture.receipt_path, **result.model_dump()}))
    raise typer.Exit(0 if result.valid else capture.exit_code or 1)
