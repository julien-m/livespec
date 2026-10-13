"""Thin ``livespec delivery`` command group: lane and end-of-feature review (feature 086).

Handlers parse options, call ``validator.delivery`` services and map outcomes to exit
codes: 0 evaluated or accepted, 1 refused or not current, 2 usage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from validator.delivery.lane import DeliveryInputError, LaneDecision, evaluate_lane
from validator.delivery.review import (
    KINDS,
    Kind,
    ReviewOutcome,
    prepare_scope,
    record_report,
    verify_review,
)

from ._common import require_specs_root

delivery_app = typer.Typer(name="delivery", help="Risk-proportional delivery lane and review.")
review_app = typer.Typer(name="review", help="One independent review of the complete diff.")
delivery_app.add_typer(review_app, name="review")

EXIT_USAGE = 2
FEATURE = Annotated[str, typer.Option("--feature", help="Feature slug.")]
MODEL = Annotated[str, typer.Option("--model", help="Reviewer model of the spec review.")]
MAX_CHARS = Annotated[
    int | None, typer.Option("--review-max-chars", help="Budget of the spec review.")
]
JSON_OUT = Annotated[bool, typer.Option("--json", help="Print JSON on stdout.")]


# @spec FR-001: Delivery command group
#   — .specs/features/086-risk-proportional-delivery/spec.md#fr-001
def register(app: typer.Typer) -> None:
    """Register the ``livespec delivery`` command group on ``app``."""
    app.add_typer(delivery_app, name="delivery")


def _usage(message: str) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(EXIT_USAGE)


def _lane(root: Path, feature: str, model: str, max_chars: int | None) -> LaneDecision:
    try:
        return evaluate_lane(root, feature, model, max_chars)
    except DeliveryInputError as exc:
        _usage(str(exc))


def _emit_outcome(title: str, outcome: ReviewOutcome, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(outcome.to_json()))
        return
    typer.echo(f"{title}: {'OK' if not outcome.reasons else 'REFUSED'} ({outcome.verdict})")
    for reason in outcome.reasons:
        typer.echo(f"  - {reason.code}: {reason.detail}")
    typer.echo(f"Receipt: {outcome.receipt_path}")


@delivery_app.command("lane")
def lane_command(
    feature: FEATURE, model: MODEL = "", max_chars: MAX_CHARS = None, as_json: JSON_OUT = False
) -> None:
    """Decide the light or full lane from the reviewed QE classification."""
    decision = _lane(require_specs_root(), feature, model, max_chars)
    if as_json:
        typer.echo(json.dumps(decision.to_json()))
    else:
        typer.echo(f"Delivery lane: {decision.lane.upper()}")
        typer.echo(f"Criticality: {decision.criticality}; blast radius: {decision.blast_radius}")
        for reason in decision.reasons:
            typer.echo(f"  - {reason.code}: {reason.detail}")
    raise typer.Exit(0)


@review_app.command("prepare")
def prepare_command(
    feature: FEATURE,
    base: Annotated[str, typer.Option("--base", help="Revision the feature started from.")],
    model: MODEL = "",
    max_chars: MAX_CHARS = None,
    as_json: JSON_OUT = False,
) -> None:
    """Hash every path of the feature diff for the independent reviewer."""
    root = require_specs_root()
    decision = _lane(root, feature, model, max_chars)
    scope, error = prepare_scope(root, feature, base, decision.lane)
    payload = {**scope, "error": error, "protocol": "system/delivery-review.md"}
    if as_json:
        typer.echo(json.dumps(payload))
    elif error:
        typer.echo(f"Delivery review scope: {error} {scope.get('detail', '')}".rstrip())
    else:
        typer.echo(f"Delivery review scope: {len(scope['files'])} file(s), lane {decision.lane}")
        for path in scope["files"]:
            typer.echo(f"  {path}")
    raise typer.Exit(1 if error else 0)


@review_app.command("record")
def record_command(
    feature: FEATURE,
    kind: Annotated[str, typer.Option("--kind", help="combined, review or audit.")],
    report: Annotated[Path, typer.Option("--report", help="Reviewer report JSON.")],
    as_json: JSON_OUT = False,
) -> None:
    """Record the reviewer report as one round when it covers the prepared scope."""
    if kind not in KINDS:
        _usage("--kind must be combined, review or audit")
    root = require_specs_root()
    try:
        outcome = record_report(root, feature, _kind(kind), report)
    except DeliveryInputError as exc:
        _usage(str(exc))
    _emit_outcome("Delivery review record", outcome, as_json)
    raise typer.Exit(1 if outcome.reasons else 0)


def _kind(value: str) -> Kind:
    for kind in KINDS:
        if kind == value:
            return kind
    _usage(f"unknown kind {value!r}")


@review_app.command("verify")
def verify_command(
    feature: FEATURE, model: MODEL = "", max_chars: MAX_CHARS = None, as_json: JSON_OUT = False
) -> None:
    """Check that the reviews required by the current lane passed and are current."""
    root = require_specs_root()
    decision = _lane(root, feature, model, max_chars)
    try:
        outcome = verify_review(root, feature, decision.lane)
    except DeliveryInputError as exc:
        _usage(str(exc))
    _emit_outcome(f"Delivery review ({decision.lane} lane)", outcome, as_json)
    raise typer.Exit(1 if outcome.reasons else 0)
