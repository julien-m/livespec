"""Source-bound clarification on the existing validate surface (078 FR-008)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import typer
from pydantic import BaseModel, ConfigDict

from validator.clarify_inventory import (
    collect_clarification_inventory,
    persist_clarification_decision,
)
from validator.semantic.review_files import prepare_feature_review, review_receipt_path


class ClarificationAnswer(BaseModel):
    """An accepted answer targets one current question, never a stale positional index."""

    model_config = ConfigDict(extra="forbid", strict=True)
    requirement_id: str
    decision_key: str
    source_hash: str
    answer: str


def clarify_io(
    root: Path, feature: str, *, model: str, max_chars: int | None, answer_path: Path | None
) -> None:
    """Return the full inventory or apply an accepted current answer without ID churn."""
    spec = root / ".specs/features" / feature / "spec.md"
    prepared = prepare_feature_review(root, feature, "spec", model, max_chars)
    inventory = collect_clarification_inventory(
        spec, review_receipt=review_receipt_path(root, feature, "spec"), prepared_review=prepared
    )
    if answer_path:
        answer = ClarificationAnswer.model_validate_json(answer_path.read_text(encoding="utf-8"))
        if answer.source_hash != inventory.source_hash:
            raise ValueError("clarification_answer_stale")
        matching = [
            item
            for item in inventory.inventory
            if item.requirement_id == answer.requirement_id
            and item.decision_key == answer.decision_key
        ]
        if len(matching) != 1:
            raise ValueError("clarification_question_not_unique_or_current")
        new_hash = persist_clarification_decision(spec, matching[0], answer.answer)
        typer.echo(json.dumps({"source_hash": new_hash, "dependent_review": "stale"}))
        raise typer.Exit(0)
    typer.echo(json.dumps({**asdict(inventory), "blocking": inventory.blocking}, default=str))
    raise typer.Exit(1 if inventory.blocking else 0)
