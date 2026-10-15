"""Reviewer model and budget from options, else the semantic configuration (feature 093).

Distinct from ``review_identity``, which fingerprints a prepared review context.
"""

from __future__ import annotations

import reprlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from .config import SemanticConfig, load_semantic_config

# Character budgets, not tokens: the bounds of the execution-mapping review budget.
REVIEW_MAX_CHARS_MIN = 1000
REVIEW_MAX_CHARS_MAX = 200000

Source = Literal["option", "configuration"]
# Placeholders a runtime may print instead of its model; they name no reviewer.
_UNNAMED = frozenset({"", "default", "unknown"})


class ReviewIdentityError(ValueError):
    """No reviewer model is named, a review budget is out of bounds or the config unreadable."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True)
class ReviewIdentity:
    """Resolved reviewer model and budget; ``source`` names where the model came from."""

    model: str
    max_chars: int
    source: Source


def review_budget(max_chars: int | None, config: SemanticConfig) -> int:
    """Return the explicit budget, else the configured one; refuse it out of bounds.

    Raises:
        ReviewIdentityError: ``review_max_chars_out_of_bounds``; a budget is never clamped.
    """
    # YAML may hold any value; ``bool`` is an ``int`` subclass and is refused too.
    budget = cast(object, max_chars if max_chars is not None else config.review_max_chars)
    origin = "--review-max-chars" if max_chars is not None else "review_max_chars"
    if (
        isinstance(budget, int)
        and not isinstance(budget, bool)
        and REVIEW_MAX_CHARS_MIN <= budget <= REVIEW_MAX_CHARS_MAX
    ):
        return budget
    raise ReviewIdentityError(
        "review_max_chars_out_of_bounds",
        f"{origin} {reprlib.repr(budget)} is not an integer from {REVIEW_MAX_CHARS_MIN} "
        f"to {REVIEW_MAX_CHARS_MAX}",
    )


def named_model(value: object) -> str:
    """Return the stripped model ``value`` names, or '' for a placeholder or non-string."""
    model = value.strip() if isinstance(value, str) else ""
    return "" if model.lower() in _UNNAMED else model


def configured_model(config: SemanticConfig) -> str:
    """Return ``review_model``, else the first configured reviewer, else ''."""
    # YAML may hold any value: only a string other than a placeholder names a model.
    raw_reviewers = cast(object, config.review_reviewers)
    reviewers = cast(list[object], raw_reviewers) if isinstance(raw_reviewers, list) else []
    candidates = (cast(object, config.review_model), *reviewers)
    return next((m for m in map(named_model, candidates) if m), "")


# @spec FR-001: One resolution of model and budget
#   — .specs/features/093-configured-review-identity/spec.md#fr-001
def resolve_review_identity(
    project_root: Path, model: str = "", max_chars: int | None = None
) -> ReviewIdentity:
    """Resolve the reviewer identity shared by goals, progressions and the delivery lane.

    Args:
        project_root: Project whose ``.specs/semantic/config.yaml`` is read.
        model: ``--model`` value; '' reads ``review_model`` from the configuration.
        max_chars: ``--review-max-chars`` value; None reads ``review_max_chars``.

    Returns:
        The explicit values, else the configured ones.

    Raises:
        ReviewIdentityError: ``review_model_required`` when neither names a model,
            ``review_max_chars_out_of_bounds``, or ``review_config_invalid`` when the
            configuration cannot be read or parsed.
    """
    try:
        config = load_semantic_config(project_root / ".specs")
    except (OSError, ValueError) as exc:  # UnicodeDecodeError is a ValueError
        detail = f"{type(exc).__name__} reading .specs/semantic/config.yaml"
        raise ReviewIdentityError("review_config_invalid", detail) from exc
    budget = review_budget(max_chars, config)
    source: Source = "option" if model else "configuration"
    resolved = named_model(model) if model else configured_model(config)
    if not resolved:
        raise ReviewIdentityError(
            "review_model_required",
            "pass --model or set review_model in .specs/semantic/config.yaml",
        )
    return ReviewIdentity(resolved, budget, source)
