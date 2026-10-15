"""Thin ``livespec delivery`` command group: lane and end-of-feature review (feature 086).

Handlers parse options, call ``validator.delivery`` services and map outcomes to exit
codes: 0 evaluated or accepted, 1 refused or not current, 2 usage.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, NoReturn

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
from validator.delivery.revision import close_revision, open_revision, read_revision
from validator.identity import SLUG_REGEX
from validator.semantic.review_identity_config import ReviewIdentityError

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
    # @spec FR-001: An unresolved model stops the lane instead of the full lane
    #   — .specs/features/093-configured-review-identity/spec.md#fr-001
    except ReviewIdentityError as exc:
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
    try:
        scope, error = prepare_scope(root, feature, base, decision.lane)
    except DeliveryInputError as exc:
        _usage(str(exc))
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


revision_app = typer.Typer(name="revision", help="Revise the spec during implementation.")
delivery_app.add_typer(revision_app, name="revision")


def _emit_revision(payload: dict[str, object], error: str, as_json: bool) -> NoReturn:
    if as_json:
        typer.echo(json.dumps({**payload, "error": error}))
    else:
        state = "open" if payload.get("open") else "closed"
        typer.echo(f"Spec revision: {state}" + (f" ({error})" if error else ""))
    raise typer.Exit(1 if error else 0)


# @spec FR-004: Spec revision commands
#   — .specs/features/089-stable-review-identity/spec.md#fr-004
@revision_app.command("open")
def revision_open_command(
    feature: FEATURE, model: MODEL = "", max_chars: MAX_CHARS = None, as_json: JSON_OUT = False
) -> None:
    """Record the current spec and plan reviews before revising the spec."""
    payload, error = _revision(open_revision, feature, model, max_chars)
    _emit_revision(payload, error, as_json)


@revision_app.command("close")
def revision_close_command(
    feature: FEATURE, model: MODEL = "", max_chars: MAX_CHARS = None, as_json: JSON_OUT = False
) -> None:
    """Close the revision once the revised spec and plan are reviewed again."""
    payload, error = _revision(close_revision, feature, model, max_chars)
    _emit_revision(payload, error, as_json)


@revision_app.command("status")
def revision_status_command(feature: FEATURE, as_json: JSON_OUT = False) -> None:
    """Print the open revision record, if any."""
    root = require_specs_root()
    _feature_or_usage(root, feature)
    try:
        record = read_revision(root, feature)
    except ValueError as exc:
        _usage(str(exc))
    _emit_revision({**(record or {"feature": feature}), "open": record is not None}, "", as_json)


def _feature_or_usage(root: Path, feature: str) -> None:
    if not SLUG_REGEX.fullmatch(feature) or not (root / ".specs/features" / feature).is_dir():
        _usage(f"unknown feature {feature!r}")


def _revision(
    action: Callable[[Path, str, str, int | None], tuple[dict[str, Any], str]],
    feature: str,
    model: str,
    max_chars: int | None,
) -> tuple[dict[str, Any], str]:
    root = require_specs_root()
    _feature_or_usage(root, feature)
    try:
        return action(root, feature, model, max_chars)
    except ValueError as exc:
        _usage(str(exc))
