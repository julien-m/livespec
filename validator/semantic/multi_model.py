"""Multi-model divergence validation (experimental)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MultiModelResult:
    """Response from a single model in a multi-model validation run."""

    model: str
    response: str
    embedding: list[float] | None = None


def run_multi_model(
    question: str,
    spec_content: str,
    models: list[str],
) -> list[MultiModelResult]:
    """Run the same validation question against multiple LLM models.

    STUB: this is an experimental feature requiring multiple LLM SDKs.

    Args:
        question: Validation prompt to send to each model.
        spec_content: Spec content to include as context.
        models: List of model identifiers to query.

    Returns:
        One result per model with its response text.

    Raises:
        NotImplementedError: Always — multi-model support is not yet wired.
    """
    raise NotImplementedError(
        "Multi-model validation is experimental. "
        "Install required SDKs (openai, anthropic, google-generativeai) "
        "and configure API keys to enable."
    )


def compute_divergence(results: list[MultiModelResult]) -> float:
    """Compute divergence score across multi-model responses.

    STUB: requires embedding computation to measure response similarity.

    Args:
        results: Responses from each model to compare.

    Returns:
        Float between 0.0 (full agreement) and 1.0 (total divergence).

    Raises:
        NotImplementedError: Always — embedding support is required.
    """
    raise NotImplementedError(
        "Divergence computation requires embedding support. "
        "Install openai package and set OPENAI_API_KEY to enable."
    )
