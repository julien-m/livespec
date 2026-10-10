"""Native review transport on existing validation surface (078 FR-002, FR-015)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import typer
from pydantic import BaseModel, ConfigDict

from validator.semantic.review_api import ingest_feature_review, prepare_feature_review
from validator.semantic.review_contract import REVIEW_SCHEMA


class NativeReviewInput(BaseModel):
    """Actual raw reviewer messages; never accept caller-written verdicts."""

    model_config = ConfigDict(extra="forbid", strict=True)
    raw_results: list[str]
    synthesis: str | None = None


def review_io(
    feature_dir: Path,
    *,
    prepare: str | None,
    ingest: Path | None,
    kind: str,
    model: str,
    max_chars: int | None = None,
) -> None:
    """Prepare or ingest one complete native review, then return through the CLI."""
    selected = prepare or kind
    if selected == "acceptance":
        _acceptance_io(feature_dir, bool(prepare), ingest, model, max_chars)
        return
    if selected not in ("spec", "plan"):
        raise ValueError("review_kind_must_be_spec_plan_or_acceptance")
    review_kind: Literal["spec", "plan"] = "spec" if selected == "spec" else "plan"
    root = feature_dir.parents[2]
    if prepare:
        prepared = prepare_feature_review(root, feature_dir.name, review_kind, model, max_chars)
        typer.echo(
            json.dumps({"prepared": prepared.model_dump(), "response_schema": REVIEW_SCHEMA})
        )
        raise typer.Exit(0 if prepared.complete else 1)
    if ingest is None:
        raise ValueError("native_review_input_required")
    raw = NativeReviewInput.model_validate_json(ingest.read_text(encoding="utf-8"))
    receipt, path = ingest_feature_review(
        root,
        feature_dir.name,
        review_kind,
        raw.raw_results,
        raw.synthesis,
        model=model,
        max_chars=max_chars,
    )
    typer.echo(json.dumps({"receipt_path": str(path), **receipt.model_dump()}))
    raise typer.Exit(0 if receipt.complete and receipt.ready else 1)


def _acceptance_io(
    feature_dir: Path,
    prepare: bool,
    ingest: Path | None,
    model: str,
    max_chars: int | None,
) -> None:
    from validator.semantic.acceptance_review import (
        ingest_acceptance_review,
        prepare_acceptance_review,
    )

    root, feature = feature_dir.parents[2], feature_dir.name
    if prepare:
        prepared = prepare_acceptance_review(root, feature, model, max_chars)
        typer.echo(
            json.dumps({"prepared": prepared.model_dump(), "response_schema": REVIEW_SCHEMA})
        )
        raise typer.Exit(0 if prepared.complete else 1)
    if ingest is None:
        raise ValueError("native_review_input_required")
    raw = NativeReviewInput.model_validate_json(ingest.read_bytes().decode("utf-8"))
    receipt, path = ingest_acceptance_review(
        root, feature, raw.raw_results, raw.synthesis, model=model, max_chars=max_chars
    )
    typer.echo(json.dumps({"receipt_path": str(path), **receipt.model_dump()}))
    raise typer.Exit(0 if receipt.complete and receipt.ready else 1)
