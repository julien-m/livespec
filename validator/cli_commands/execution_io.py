"""Existing test command adapters for independent mapping review and execution (078 FR-010)."""

from __future__ import annotations

import json
import os
import shlex
from pathlib import Path

import typer

from validator.execution_capture import capture_execution
from validator.execution_evidence import verify_execution_receipt
from validator.execution_mapping import (
    AcceptanceMapping,
    ingest_mapping_review,
    prepare_mapping_review,
)
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
) -> None:
    """Expose reviewer preparation/ingestion and actual capture, with strict certification."""
    if not feature or mapping_path is None:
        raise ValueError("execution_feature_and_acceptance_mapping_required")
    mapping_path = (root / mapping_path).resolve()
    mapping_path.relative_to(root)
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
    if not command:
        raise ValueError("execution_command_required")
    capture = capture_execution(
        shlex.split(command),
        project_root=root,
        feature=feature,
        adapter=adapter,
        env=dict(os.environ),
        acceptance_mapping=mapping_path.relative_to(root).as_posix(),
    )
    result = verify_execution_receipt(Path(capture.receipt_path), root, feature)
    typer.echo(json.dumps({"execution_receipt_path": capture.receipt_path, **result.model_dump()}))
    raise typer.Exit(0 if result.valid else 1)
